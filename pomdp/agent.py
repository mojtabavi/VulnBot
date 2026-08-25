"""BeliefAgent — the standalone POMDP control loop (R1, TL-2.1).

This is the integrator `belief_state.run_agent` has always described but never ran: a
belief-first loop that ties the policy π, the Executor (R3), the Bayesian Updater, and the
Belief Store together.

    b0 = new_belief + priors.seed_vuln_priors           # conventional b0
    repeat until goal / step-cap:
        a   = choose_action(candidates, b)              # π  (info-gain vs exploit-value)
        a   = (HITL gate — approve/deny/step, best-effort)
        obs = executor.run(a)                           # A → O  (normalized Observation)
        b   = update_belief(b, a, obs.raw, llm, samples)#  Z + soft Bayes
        store.save(b)                                   #  one file per step = the trace

The belief MATH is imported, never re-implemented — every number comes from
`pomdp/belief_state.py` (`choose_action`, `update_belief`, `score_action`) and
`pomdp/priors.py`. The loop **never branches on the hidden true state S**; it only ever reads
and writes the agent's information-state `b`. Every side channel (events, HITL control) is
best-effort: a failure there must never break the run.

Deliberately stdlib + `pomdp/` + `executor/` only (all stdlib-only), so this imports without
the RAG/ML stack — the same constraint the rest of `pomdp/` holds. Holds no offensive code:
the Executor is the only thing that touches Kali.

TL boundaries: TL-2.1 (this file) is the loop + default candidate generation + goal check +
the event/HITL seams. TL-2.2 points `belief_state.run_agent` here. TL-2.3 wires
`OCTOPUS_Z_SAMPLES`. TL-2.4 fills in the full event set. TL-4.4 fills the HITL gate.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from pomdp import priors
from pomdp.belief_state import (
    Action, ActionType, new_belief, add_host, choose_action, update_belief, score_action,
    z_samples,
)
from pomdp.belief_store import BeliefStore

__all__ = ["BeliefAgent", "run_agent"]

# Type of the Z-likelihood LLM the Updater needs: a plain `str -> str` callable.
BeliefLLM = Callable[[str], str]
# A candidate generator maps the current belief → the actions the policy may choose among.
CandidateFn = Callable[[Dict[str, Any]], List[Action]]
# A goal predicate: given the belief and the last Observation, is the run done?
GoalFn = Callable[[Dict[str, Any], Optional[Any]], bool]
# A HITL gate: given a proposed action, return True to run it, False to skip (deny).
ApproveFn = Callable[[Action], bool]

# Belief that a host is rooted, above which the default goal predicate stops the run.
_ROOT_BELIEF_STOP = 0.5
# Substrings in raw tool output that strongly indicate root on the target.
_ROOT_MARKERS = ("uid=0", "root@", "# id", "gained root", "root shell")

# Action types high-impact enough to gate on human approval by default (R2, TL-4.4).
_HIGH_IMPACT = (ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC)


class BeliefAgent:
    """Runs the POMDP belief loop over an `Executor`.

    Args:
      executor:   anything with `.run(action, action_id=None) -> Observation` (R3 `Executor`).
      belief_llm: the `str -> str` callable the Updater uses for Z (per-hypothesis
                  likelihoods). REQUIRED — `update_belief` refuses to run without it.
      store:      a `BeliefStore` for the per-step belief trace (default: a fresh one).
      events:     optional event log with a best-effort `.append(type, **fields)` (R4, TL-2.4).
      approve:    optional HITL gate `Action -> bool` (default: allow everything; TL-4.4).
      max_steps:  hard cap on loop iterations (keeps a run bounded).
      samples:    self-consistency Z samples per update (TL-2.3 reads `OCTOPUS_Z_SAMPLES`).
      goal_fn:    optional stop predicate `(belief, last_obs) -> bool` (default: root-reached).
    """

    def __init__(
        self,
        executor: Any,
        belief_llm: BeliefLLM,
        store: Optional[BeliefStore] = None,
        events: Optional[Any] = None,
        approve: Optional[ApproveFn] = None,
        control: Optional[Any] = None,
        step: bool = False,
        max_steps: int = 20,
        samples: Optional[int] = None,
        goal_fn: Optional[GoalFn] = None,
    ):
        if belief_llm is None:
            raise ValueError("BeliefAgent requires a belief_llm (str -> str) for the Z likelihoods.")
        self.executor = executor
        self.belief_llm = belief_llm
        self.store = store or BeliefStore()
        self.events = events
        # HITL: `approve` is the simple bool seam (tests); `control` is a `utils.control.ControlServer`
        # (or duck-typed connected()/send()/recv()) for the real octopus back-channel (R2, TL-4.4).
        self.approve = approve
        self.control = control
        self.step_mode = bool(step)  # step-through: gate EVERY action, not just high-impact ones
        self.max_steps = max(1, int(max_steps))
        self.samples = _resolve_samples(samples)
        self.goal_fn = goal_fn or _default_goal

    # ── the loop ────────────────────────────────────────────────────────────────
    def run(
        self,
        session_id: str,
        hosts: Optional[Sequence[str]] = None,
        vuln_ids: Optional[Sequence[str]] = None,
        candidates_fn: Optional[CandidateFn] = None,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the belief loop for `session_id` and return the final belief.

        `hosts` are the initially known targets (may be empty for a recon-first run);
        `vuln_ids` seed the b0 vuln priors (via `priors.seed_vuln_priors`) on every host.
        `candidates_fn` overrides the default candidate generation; `target` is a convenience
        for the common single-host case (added to `hosts`). Never raises out of the loop body —
        an executor/updater hiccup is logged and the loop continues to the step cap.
        """
        host_list = list(hosts or [])
        if target and target not in host_list:
            host_list.append(target)
        vid_list = list(vuln_ids or [])

        # b0: conventional priors + seeded vuln priors (same P(present) on each known host).
        seeded = priors.seed_vuln_priors(vid_list) if vid_list else {}
        vuln_priors = {h: dict(seeded) for h in host_list} if seeded else None
        belief = new_belief(session_id, host_list, vuln_priors)
        self._save(belief, session_id)
        self._emit("run_start", session_id=session_id, hosts=host_list, vuln_ids=vid_list,
                   max_steps=self.max_steps, samples=self.samples)

        gen = candidates_fn or self._default_candidates
        last_obs: Optional[Any] = None

        for step in range(self.max_steps):
            if self._poll_control() == "quit":  # a between-steps pause/quit from the CLI (R2)
                self._emit("decision", reason="quit (user)", step=step)
                break

            candidates = self._safe_candidates(gen, belief)
            if not candidates:
                self._emit("decision", reason="no candidate actions", step=step)
                break

            action = choose_action(candidates, belief)  # π
            # NOTE: `action_type` (not `type`) — `type` is EventLog.append's positional param.
            self._emit("action_selected", step=step, action=action.name, action_type=action.type,
                       host=action.host, tool=action.tool)
            self._emit("score", step=step, action=action.name, action_type=action.type,
                       score=self._score(action, belief))  # R for the chosen action (belief before)

            decision = self._gate(action, step)  # "approve" | "deny" | "quit" (R2, TL-4.4)
            if decision == "quit":
                self._emit("decision", reason="quit (user)", step=step)
                break
            if decision == "deny":
                continue  # denied → skip this action, keep the belief, try again next step

            obs = self._execute(action)
            last_obs = obs
            self._emit_observation(step, obs)  # full Observation.to_dict() (R4 observation record)

            prev_step = int(belief.get("step", 0))
            belief = self._update(belief, action, obs)
            self._save(belief, session_id)
            if int(belief.get("step", 0)) > prev_step:  # only on a REAL update (not a failed/kept one)
                self._emit_belief_events(belief)  # belief_update (prior/posterior) + llm_likelihoods (Z)

            if self.goal_fn(belief, last_obs):
                self._emit("decision", reason="goal reached", step=step)
                break

        self._emit("run_end", session_id=session_id, steps=belief.get("step"))
        self._write_manifest(session_id, belief)  # R4 TL-3.3: link events.jsonl ↔ belief trace
        return belief

    # ── default candidate generation ────────────────────────────────────────────
    def _default_candidates(self, belief: Dict[str, Any]) -> List[Action]:
        """Recon (probe each host) + priors-enriched exploit actions for seeded vulns.

        A minimal, overridable generator so the loop is runnable out of the box: one recon
        action per known host, plus one exploit action per vuln the belief already carries
        (enriched with `value`/`cost`/`detection_risk` from `priors`). Real deployments pass a
        `candidates_fn` that mines recon output for services/CVEs and names MSF modules.
        """
        out: List[Action] = []
        for host, hostb in (belief.get("hosts") or {}).items():
            out.append(Action(name=f"recon:{host}", type=ActionType.RECON, host=host, tool="nmap"))
            for vid in (hostb.get("vulns") or {}):
                a = Action(name=vid, type=ActionType.EXPLOIT, host=host, params={"vuln": vid})
                out.append(priors.enrich_action(a))  # fill R inputs, never raises
        return out

    # ── guarded internals (best-effort; never break the run) ────────────────────
    def _safe_candidates(self, gen: CandidateFn, belief: Dict[str, Any]) -> List[Action]:
        try:
            return list(gen(belief) or [])
        except Exception:  # noqa: BLE001 - a bad generator must not kill the loop
            return []

    # ── HITL gate (R2, TL-4.4) ──────────────────────────────────────────────────
    def _needs_approval(self, action: Action) -> bool:
        """Gate an action on human approval when it is high-impact (exploit/lateral/privesc) or when
        step-through mode is on (gate everything)."""
        return self.step_mode or getattr(action, "type", None) in _HIGH_IMPACT

    def _gate(self, action: Action, step: int) -> str:
        """Decide whether to run `action`: returns "approve" | "deny" | "quit".

        Precedence: the simple `approve` bool callback (tests) wins if set; otherwise the control
        socket gates high-impact/step actions by blocking on a reply. No connected front-end, or
        no approval needed, ⇒ "approve" (auto) — a missing CLI must never block a run."""
        if self.approve is not None:  # legacy bool seam (tests): approve/deny only
            try:
                approved = bool(self.approve(action))
            except Exception:  # noqa: BLE001 - a broken gate must not block the run; fail open
                approved = True
            self._emit("approval_request", step=step, action=action.name,
                       action_type=action.type, host=action.host)
            self._emit("approval_result", step=step, action=action.name, approved=approved)
            return "approve" if approved else "deny"

        if not self._ctrl_connected() or not self._needs_approval(action):
            return "approve"  # no front-end, or a low-impact action → proceed without blocking

        risk = "high" if getattr(action, "type", None) in _HIGH_IMPACT else "normal"
        self._emit("approval_request", step=step, action=action.name,
                   action_type=action.type, host=action.host, risk=risk)
        self._ctrl_send({"event": "approval_request", "action": action.name,
                         "type": action.type, "host": action.host, "risk": risk})
        decision = self._await_decision()
        self._emit("approval_result", step=step, action=action.name,
                   approved=(decision == "approve"), decision=decision)
        return decision

    def _await_decision(self) -> str:
        """Block on control replies until the human approves/denies/quits. `step` runs this one then
        arms step-through; `pause`/`resume` are acknowledged and keep waiting. A dropped client
        (recv None) ⇒ "approve" (auto) so a lost front-end never wedges the run."""
        while True:
            frame = self._ctrl_recv(timeout=None)
            if frame is None:
                return "approve"  # client gone → proceed
            cmd = (frame or {}).get("cmd")
            if cmd == "approve":
                return "approve"
            if cmd == "deny":
                return "deny"
            if cmd == "quit":
                return "quit"
            if cmd == "step":
                self.step_mode = True
                return "approve"  # run this one; every subsequent action will gate too
            if cmd == "pause":
                self._ctrl_send({"event": "paused"})
                continue
            if cmd == "resume":
                self._ctrl_send({"event": "resumed"})
                continue
            # unknown command → keep waiting for a decisive one

    def _poll_control(self) -> Optional[str]:
        """Between steps: non-blocking check for a `pause`/`quit`/`step` command. A `pause` blocks
        here until `resume`/`quit`; returns "quit" to stop the run, else None. Best-effort."""
        if not self._ctrl_connected():
            return None
        frame = self._ctrl_recv(timeout=0.0)  # non-blocking poll
        if frame is None:
            return None
        cmd = (frame or {}).get("cmd")
        if cmd == "quit":
            return "quit"
        if cmd == "step":
            self.step_mode = True
            return None
        if cmd == "pause":
            self._ctrl_send({"event": "paused"})
            while True:  # hold here until told to continue
                f = self._ctrl_recv(timeout=None)
                if f is None:
                    return None  # client gone → resume automatically
                c = (f or {}).get("cmd")
                if c == "resume":
                    self._ctrl_send({"event": "resumed"})
                    return None
                if c == "quit":
                    return "quit"
                if c == "step":
                    self.step_mode = True
                    return None
        return None

    # guarded control-socket shims (duck-typed; a bad/missing control never breaks the run)
    def _ctrl_connected(self) -> bool:
        ctrl = self.control
        if ctrl is None:
            return False
        try:
            return bool(ctrl.connected())
        except Exception:  # noqa: BLE001
            return False

    def _ctrl_send(self, obj: Dict[str, Any]) -> None:
        try:
            self.control.send(obj)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass

    def _ctrl_recv(self, timeout: Optional[float]) -> Optional[Dict[str, Any]]:
        try:
            return self.control.recv(timeout)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            return None

    def _execute(self, action: Action) -> Any:
        """Run the action through the Executor. The R3 Executor never raises, but guard anyway
        and synthesize a failure Observation so the Updater always receives an O."""
        try:
            return self.executor.run(action)
        except Exception as e:  # noqa: BLE001 - defensive: keep the loop alive
            from pomdp.observation import Observation, new_action_id
            return Observation.failure(new_action_id(), "none", getattr(action, "type", "?"),
                                       error=f"executor raised: {e}", host=getattr(action, "host", None))

    def _update(self, belief: Dict[str, Any], action: Action, obs: Any) -> Dict[str, Any]:
        try:
            raw = getattr(obs, "raw", "") or ""
            return update_belief(belief, action, raw, llm=self.belief_llm, samples=self.samples)
        except Exception:  # noqa: BLE001 - a Z/update failure softens nothing; keep prior belief
            self._emit("error", where="update_belief", action=getattr(action, "name", "?"))
            return belief

    def _save(self, belief: Dict[str, Any], session_id: str) -> None:
        try:
            self.store.save(belief, session_id)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass

    def _write_manifest(self, session_id: str, belief: Dict[str, Any]) -> None:
        """Ask the event log to write the run manifest linking events.jsonl ↔ the belief trace dir
        (R4, TL-3.3). Best-effort — only if the sink supports it (a real `EventLog`)."""
        ev = self.events
        if ev is None or not hasattr(ev, "write_manifest"):
            return
        try:
            belief_dir = self.store.run_dir(session_id) if hasattr(self.store, "run_dir") else None
            ev.write_manifest(belief_dir=belief_dir, steps=belief.get("step"))
        except Exception:  # noqa: BLE001 - manifest is a convenience, never fatal
            pass

    def _emit(self, etype: str, **fields: Any) -> None:
        """Append an event to the log if one is attached (R4). Best-effort — never fatal."""
        ev = self.events
        if ev is None:
            return
        try:
            ev.append(etype, **fields)
        except Exception:  # noqa: BLE001 - a dead event sink must not break the run
            pass

    def _score(self, action: Action, belief: Dict[str, Any]) -> Optional[float]:
        """R(action | belief) for the chosen action (belief BEFORE the update), for the `score`
        event. Guarded — a scoring hiccup must not stop the loop."""
        try:
            return round(float(score_action(action, belief)), 4)
        except Exception:  # noqa: BLE001
            return None

    def _emit_observation(self, step: int, obs: Any) -> None:
        """Emit the full Observation as the R4 `observation` record (obs.to_dict() verbatim), minus
        the obs's own `ts` so the event's log-time `ts` is preserved."""
        try:
            d = obs.to_dict() if hasattr(obs, "to_dict") else {}
        except Exception:  # noqa: BLE001
            d = {}
        d.pop("ts", None)
        self._emit("observation", step=step, **d)

    def _emit_belief_events(self, belief: Dict[str, Any]) -> None:
        """From `meta.last_update` (written by `update_belief`, TL-3.2): a `belief_update` record with
        the prior/posterior over the touched factor, and a SELF-CONTAINED `llm_likelihoods` evidence
        record carrying Z at the Z-point plus the belief before/after and the action that produced it
        — so the LogView (TL-5.2) can render the evidence without cross-referencing other records (R4)."""
        lu = (belief.get("meta") or {}).get("last_update") or {}
        self._emit("belief_update", step=belief.get("step"), host=lu.get("host"),
                   factor=lu.get("factor"), key=lu.get("key"),
                   prior=lu.get("prior"), posterior=lu.get("posterior"))
        if lu.get("z") is not None:
            self._emit("llm_likelihoods", step=belief.get("step"), host=lu.get("host"),
                       factor=lu.get("factor"), key=lu.get("key"), action=lu.get("action"),
                       z=lu.get("z"), prior=lu.get("prior"), posterior=lu.get("posterior"))


def _resolve_samples(samples: Optional[int]) -> int:
    """Z self-consistency sample count. Explicit arg wins; else the shared
    `belief_state.z_samples()` (`OCTOPUS_Z_SAMPLES`, TL-2.3). Clamped to ≥ 1."""
    if samples is not None:
        return max(1, int(samples))
    return z_samples()


def _default_goal(belief: Dict[str, Any], last_obs: Optional[Any]) -> bool:
    """Default stop predicate: a host is believed rooted, or the last observation clearly
    shows root on the target. Reads only the belief + the Observation — never S."""
    for hostb in (belief.get("hosts") or {}).values():
        if float((hostb.get("access") or {}).get("root", 0.0)) >= _ROOT_BELIEF_STOP:
            return True
    if last_obs is not None:
        raw = (getattr(last_obs, "raw", "") or "").lower()
        atype = getattr(last_obs, "action_type", "")
        if getattr(last_obs, "success", None) is True and atype in (ActionType.PRIVESC, ActionType.EXPLOIT):
            if any(m in raw for m in _ROOT_MARKERS):
                return True
    return False


def run_agent(executor: Any, belief_llm: BeliefLLM, session_id: str, **kwargs: Any) -> Dict[str, Any]:
    """Module-level convenience the `belief_state.run_agent` delegator (TL-2.2) will call.

    Splits BeliefAgent construction kwargs from `.run(...)` kwargs so a caller can pass both
    in one flat call. Returns the final belief.
    """
    ctor_keys = ("store", "events", "approve", "control", "step", "max_steps", "samples", "goal_fn")
    ctor = {k: kwargs.pop(k) for k in ctor_keys if k in kwargs}
    agent = BeliefAgent(executor, belief_llm, **ctor)
    return agent.run(session_id, **kwargs)
