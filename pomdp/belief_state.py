"""Explicit POMDP belief-state for the Octopus belief agent.

╔══════════════════════════════════════════════════════════════════════════════╗
║  SCAFFOLD / STUB — Phase 2.1                                                    ║
║  This file defines the *interface* and the *belief data shape* only. The        ║
║  belief MATH (Bayesian update, reward, policy) is intentionally left as          ║
║  NotImplementedError for the thesis author to fill in Phases 2.2–2.5, or to      ║
║  be replaced wholesale by the author's own belief_state.py with the SAME public  ║
║  names. Nothing here branches on the hidden true state S — that is the point.    ║
╚══════════════════════════════════════════════════════════════════════════════╝

POMDP tuple  <S, A, O, T, Z, R, b, γ>  →  where it lives:
  S   hidden true config (OS/versions/vulns/access/honeypot). NEVER observed here;
      lab ground truth only.
  b   factored JSON belief over S. Produced by `new_belief` / `new_host_prior`,
      persisted by `belief_store.BeliefStore`.
  A   recon / exploit / lateral / privesc. Represented by `Action`; executed as
      tools in the kali container (Executor).
  O   raw tool output from kali. Passed into `update_belief` as `observation`.
  Z   P(O | hypothesis). Supplied by an LLM (per-hypothesis likelihoods) inside
      `update_belief`; the CODE normalizes (Bayes). Filled in Phase 2.2/2.3.
  T   effect of an action on state. Reasoned about inside `update_belief`.
  R   goal value − cost − detection risk. Computed by `score_action` (Phase 2.5).
  π   belief → action. `choose_action` (Phase 2.4).
  γ   discount factor. `GAMMA`.

Belief factoring (per host), all values are probabilities in [0, 1]:
  {
    "os":       {"linux": p, "windows": p, "other": p, "unknown": p},   # sums to 1
    "services": { "<port/name>": {"present": p, "absent": p} },         # each pair sums to 1
    "vulns":    { "<cve/id>":    {"present": p, "absent": p} },         # seeded from CVSS/
                                                                        #   exploit-maturity (2.5)
    "access":   {"none": p, "user": p, "root": p},                      # sums to 1
    "honeypot_likelihood": p,                                           # P(host is a honeypot)
  }
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "GAMMA", "OS_CLASSES", "ACCESS_LEVELS", "ActionType", "Action",
    "new_host_prior", "new_belief", "add_host",
    "Z_PROMPT_TEMPLATE", "update_belief", "score_action", "choose_action", "run_agent",
    "z_samples",
]

# Discount factor γ for the (belief) MDP. Conventional default; author may tune.
GAMMA: float = 0.95


def z_samples(default: int = 1) -> int:
    """Self-consistency Z-sample count from the env (`OCTOPUS_Z_SAMPLES`), clamped to ≥ 1.

    The ONE source of truth for how many LLM samples the Updater averages per belief update
    (TL-2.3), so the standalone `BeliefAgent` loop and the legacy Role updater agree. `samples>1`
    averages Z across calls to reduce estimator variance (self-consistency); default 1 = one call.
    """
    try:
        return max(1, int(os.environ.get("OCTOPUS_Z_SAMPLES", str(default))))
    except (TypeError, ValueError):
        return max(1, int(default))

# Likelihood floor: keeps the update SOFT — a failed observation moves mass but never
# collapses a hypothesis to 0 (e.g. a failed exploit 0.70 -> ~0.50, not -> 0).
EPS: float = 1e-3

# OS hypothesis classes. "unknown" carries the "I don't know" mass in the b0 prior.
OS_CLASSES: tuple[str, ...] = ("linux", "windows", "other", "unknown")

# Access-level hypotheses on a host.
ACCESS_LEVELS: tuple[str, ...] = ("none", "user", "root")


# ── Actions (A) ───────────────────────────────────────────────────────────────
class ActionType:
    RECON = "recon"
    EXPLOIT = "exploit"
    LATERAL = "lateral"
    PRIVESC = "privesc"


@dataclass
class Action:
    """A candidate action the policy chooses among.

    `value`, `cost`, `detection_risk` are the reward ingredients R feeds on; they
    are populated from priors (exploit success-rate, honeypot likelihood) in
    Phase 2.5. `tool` / `params` describe how the Executor runs it (SSH or msfrpc).
    """
    name: str
    type: str                      # one of ActionType.*
    host: Optional[str] = None     # target host this action operates on
    tool: Optional[str] = None     # e.g. "nmap", or an msf module path
    params: Dict[str, Any] = field(default_factory=dict)
    value: float = 0.0             # goal value if it succeeds
    cost: float = 0.0              # time/effort cost
    detection_risk: float = 0.0    # P(detected) contribution (honeypot-aware)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Belief construction (b0 priors) ──────────────────────────────────────────
def new_host_prior(
    host: str,
    vuln_priors: Optional[Dict[str, float]] = None,
    service_priors: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Return the conventional b0 prior for a single host.

    These are *conventional priors, not measured data* (thesis §"where the numbers
    come from"): a uniform "I don't know" over OS, no access, low honeypot prior.
    `vuln_priors` (id -> P(present)) is seeded from public signals — CVSS / exploit
    maturity from CVE/ExploitDB — in Phase 2.5; here it is optional and defaults to
    empty. Bayes washes out imperfect priors after a few observations.
    """
    n = len(OS_CLASSES)
    os_dist = {k: 1.0 / n for k in OS_CLASSES}  # uniform: maximal ignorance

    services: Dict[str, Dict[str, float]] = {}
    for name, p in (service_priors or {}).items():
        services[name] = {"present": float(p), "absent": 1.0 - float(p)}

    vulns: Dict[str, Dict[str, float]] = {}
    for vid, p in (vuln_priors or {}).items():
        vulns[vid] = {"present": float(p), "absent": 1.0 - float(p)}

    return {
        "host": host,
        "os": os_dist,
        "services": services,
        "vulns": vulns,
        "access": {"none": 1.0, "user": 0.0, "root": 0.0},
        "honeypot_likelihood": 0.05,  # low conventional prior
    }


def new_belief(
    session_id: str,
    hosts: Optional[Sequence[str]] = None,
    vuln_priors: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Return a fresh factored belief b0 for a run/session.

    `hosts` may be empty at the start of recon; hosts are added as they are
    discovered (Phase 2.2). `vuln_priors` maps host -> {vuln_id: P(present)}.
    """
    hosts = list(hosts or [])
    vuln_priors = vuln_priors or {}
    return {
        "session_id": session_id,
        "step": 0,
        "hosts": {h: new_host_prior(h, vuln_priors.get(h)) for h in hosts},
        "meta": {"gamma": GAMMA},
    }


def add_host(belief: Dict[str, Any], host: str,
             vuln_priors: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Add a newly discovered host to the belief with its b0 prior (idempotent)."""
    b = copy.deepcopy(belief)
    if host not in b["hosts"]:
        b["hosts"][host] = new_host_prior(host, vuln_priors)
    return b


# ── Belief update (Z + Bayes), reward (R), policy (π) — AUTHOR FILLS ─────────
# ── Observation model Z: the LLM supplies per-hypothesis LIKELIHOODS ─────────
# This is the thesis's answer to Sarraute (2013) / CHECKMATE: the "unobtainable"
# observation-probability tables are supplied by a learned estimator (the LLM). The
# prompt asks for LIKELIHOODS only — P(observation | hypothesis) — and the CODE does the
# Bayesian normalization. Only the DIRECTION/ORDER of the likelihoods must be right.
Z_PROMPT_TEMPLATE = """You are the OBSERVATION MODEL of a penetration-testing agent.
Estimate the LIKELIHOOD of the observed tool output UNDER each hypothesis about the host's
hidden state — that is P(observation | hypothesis), for each hypothesis independently.

STRICT RULES:
- Output a likelihood in [0,1] for every hypothesis. A likelihood is "how expected is this
  observation IF the hypothesis were true" — NOT the probability the hypothesis is true.
- Do NOT normalize; the likelihoods need not sum to 1.
- Do NOT output a posterior, a ranking, or any explanation.
- Keep the RELATIVE ORDER meaningful. For example a FAILED exploit is more expected if the
  vulnerability is ABSENT than if it is PRESENT — but never impossible, so never use exactly
  0 or 1.

Action: {action}
Factor under test: {factor}{key} on host {host}
Hypotheses: {hypotheses}
Observation (raw tool output O):
\"\"\"
{observation}
\"\"\"

Return ONLY a JSON object mapping each hypothesis to its likelihood, for example:
{example}"""


def _default_dist(hyps: Sequence[str]) -> Dict[str, float]:
    """Uniform prior over `hyps` (used when a factor is seen for the first time)."""
    n = len(hyps)
    return {h: 1.0 / n for h in hyps}


def _target_factor(action: Action, belief: Dict[str, Any]) -> Tuple[str, str, Optional[str], List[str]]:
    """Decide which belief factor this action+observation bears on.

    Returns (host, factor, key, hypotheses). `key` is None for the per-host `os` factor.
    Precedence: explicit action.params {factor,key} → exploit/lateral/privesc target a
    vuln (present/absent) → recon targets a probed service (present/absent) if given, else
    the host OS distribution.
    """
    host = action.host or (next(iter(belief.get("hosts", {})), None)) or "unknown"

    f = action.params.get("factor")
    k = action.params.get("key")
    if f == "os":
        return host, "os", None, list(OS_CLASSES)
    if f in ("services", "vulns") and k:
        return host, f, k, ["present", "absent"]

    if action.type in (ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC):
        key = action.params.get("vuln") or f"{action.type}:{action.name}"
        return host, "vulns", key, ["present", "absent"]

    # recon / fallback
    svc = action.params.get("service")
    if svc:
        return host, "services", svc, ["present", "absent"]
    return host, "os", None, list(OS_CLASSES)


def _get_dist(belief: Dict[str, Any], host: str, factor: str, key: Optional[str],
              hyps: Sequence[str]) -> Dict[str, float]:
    hostb = belief["hosts"][host]
    if factor == "os":
        return dict(hostb["os"])
    table = hostb.setdefault(factor, {})
    if key not in table:
        table[key] = _default_dist(hyps)
    return dict(table[key])


def _set_dist(belief: Dict[str, Any], host: str, factor: str, key: Optional[str],
              dist: Dict[str, float]) -> None:
    hostb = belief["hosts"][host]
    if factor == "os":
        hostb["os"] = dist
    else:
        hostb.setdefault(factor, {})[key] = dist


def _parse_likelihoods(text: str, hyps: Sequence[str]) -> Dict[str, float]:
    """Extract {hypothesis: likelihood} from an LLM reply; robust to surrounding prose."""
    obj: Dict[str, Any] = {}
    for m in re.finditer(r"\{[^{}]*\}", text or "", re.DOTALL):
        try:
            cand = json.loads(m.group(0))
            if isinstance(cand, dict):
                obj = cand  # keep the last JSON object found
        except json.JSONDecodeError:
            continue
    out: Dict[str, float] = {}
    for h in hyps:
        v = obj.get(h)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.5  # neutral when the model omits/garbles a hypothesis
        out[h] = min(1.0, max(EPS, v))  # floor at EPS → soft update
    return out


def update_belief(
    belief: Dict[str, Any],
    action: Action,
    observation: str,
    llm: Optional[Callable[[str], str]] = None,
    samples: int = 1,
) -> Dict[str, Any]:
    """Soft Bayesian belief update from observation O of `action`.

    Z (per-hypothesis likelihoods) comes from `llm` (a `str -> str` callable), never a
    hand-written table; the CODE normalizes:  posterior ∝ prior × Z. Z is floored at EPS so
    the update is SOFT (a failed exploit moves 0.70 → ~0.50, never → 0). With `samples > 1`
    the likelihoods are averaged over several LLM calls (self-consistency) to reduce noise.
    Returns a NEW belief with `step` incremented. Never reads the hidden true state S.
    """
    if llm is None:
        raise ValueError("update_belief requires an `llm` callable (str -> str) to produce Z.")

    b = copy.deepcopy(belief)
    host, factor, key, hyps = _target_factor(action, b)
    if host not in b["hosts"]:
        b["hosts"][host] = new_host_prior(host)

    prior = _get_dist(b, host, factor, key, hyps)

    # Gather Z (optionally averaged over `samples` calls for self-consistency).
    prompt = Z_PROMPT_TEMPLATE.format(
        action=f"{action.type}:{action.name}" + (f" (tool={action.tool})" if action.tool else ""),
        factor=factor,
        key=f"[{key}]" if key else "",
        host=host,
        hypotheses=", ".join(hyps),
        observation=(observation or "")[:4000],
        example=json.dumps({h: 0.5 for h in hyps}),
    )
    acc = {h: 0.0 for h in hyps}
    n = max(1, int(samples))
    for _ in range(n):
        z = _parse_likelihoods(llm(prompt), hyps)
        for h in hyps:
            acc[h] += z[h]
    z_avg = {h: acc[h] / n for h in hyps}

    # Bayes: posterior ∝ prior × Z, then normalize.
    unnorm = {h: max(prior.get(h, 1.0 / len(hyps)), 0.0) * max(z_avg[h], EPS) for h in hyps}
    total = sum(unnorm.values()) or 1.0
    posterior = {h: unnorm[h] / total for h in hyps}

    _set_dist(b, host, factor, key, posterior)
    b["step"] = int(b.get("step", 0)) + 1
    b.setdefault("meta", {})["last_update"] = {
        "step": b["step"], "host": host, "factor": factor, "key": key,
        "action": f"{action.type}:{action.name}",
        "z": z_avg, "prior": prior, "posterior": posterior,
    }
    return b


# Interim value when an action carries no priors-supplied value (keeps the 2.4 policy
# behavior continuous once score_action is live).
DEFAULT_VALUE: float = 1.0


def score_action(action: Action, belief: Dict[str, Any]) -> float:
    """Reward R(action | belief) = P(succeeds | b)·value − cost − detection.

    `value`/`cost`/`detection_risk` are populated from the priors source (`pomdp.priors`,
    Phase 2.5) from CVSS + exploit-maturity signals; here R just combines them with the
    belief. For exploit/lateral/privesc the success weight is the belief the target vuln is
    present (`P(present)`); recon "succeeds" (always yields an observation). Detection is
    driven by the target host's `honeypot_likelihood` plus the action's own
    `detection_risk`, so a honeypot-suspected host is penalized. Never reads the hidden S.
    """
    host, factor, key, hyps = _target_factor(action, belief)
    dist = _peek_dist(belief, host, factor, key, hyps)
    hostb = belief.get("hosts", {}).get(host, {})
    honeypot = float(hostb.get("honeypot_likelihood", 0.0))
    detection = honeypot + float(action.detection_risk)

    value = action.value if action.value else DEFAULT_VALUE
    p_success = 1.0 if action.type == ActionType.RECON else float(dist.get("present", 0.5))
    return p_success * value - float(action.cost) - detection


# Policy weights (π). Recon is rewarded for the uncertainty it can resolve;
# exploit/lateral/privesc for the belief they will succeed. Conventional; author may tune.
W_INFO: float = 1.0
W_EXPLOIT: float = 1.0


def _entropy(dist: Dict[str, float]) -> float:
    """Shannon entropy (nats) of a probability distribution. 0 = certain, higher = uncertain."""
    vals = [max(float(p), 0.0) for p in dist.values()]
    s = sum(vals) or 1.0
    ent = 0.0
    for p in vals:
        q = p / s
        if q > 0.0:
            ent -= q * math.log(q)
    return ent


def _peek_dist(belief: Dict[str, Any], host: str, factor: str, key: Optional[str],
               hyps: Sequence[str]) -> Dict[str, float]:
    """Read-only view of the belief distribution an action bears on (never mutates b)."""
    hostb = belief.get("hosts", {}).get(host, {})
    if factor == "os":
        return dict(hostb.get("os") or _default_dist(hyps))
    return dict((hostb.get(factor) or {}).get(key) or _default_dist(hyps))


def _action_utility(action: Action, belief: Dict[str, Any]) -> float:
    """Belief-conditioned utility of a candidate action (higher = better).

    RECON: valued by the normalized uncertainty (entropy) of the factor it probes —
    a recon action is worth more when the belief it would sharpen is uncertain.
    EXPLOIT/LATERAL/PRIVESC: valued by R = P(succeeds | belief)·value − cost − detection,
    delegating to `score_action` (Phase 2.5) when implemented, else a simple interim value.
    Detection is driven by the target host's `honeypot_likelihood` + `action.detection_risk`.
    """
    host, factor, key, hyps = _target_factor(action, belief)
    dist = _peek_dist(belief, host, factor, key, hyps)
    hostb = belief.get("hosts", {}).get(host, {})
    detection = float(hostb.get("honeypot_likelihood", 0.0)) + float(action.detection_risk)

    if action.type == ActionType.RECON:
        max_ent = math.log(len(hyps)) if len(hyps) > 1 else 1.0
        uncertainty = _entropy(dist) / max_ent if max_ent > 0 else 0.0
        return W_INFO * uncertainty - detection

    # exploit / lateral / privesc — prefer the author's reward R once 2.5 lands.
    try:
        return score_action(action, belief)
    except NotImplementedError:
        p_success = float(dist.get("present", 0.5))
        value = action.value if action.value else 1.0
        return W_EXPLOIT * p_success * value - float(action.cost) - detection


def choose_action(candidates: Sequence[Action], belief: Dict[str, Any]) -> Action:
    """Policy π: pick the next action given the current belief (argmax utility).

    Trades information gain (recon that sharpens b when it is uncertain) against exploit
    value (P(succeeds | belief) − cost − detection). Depends on `belief`: the SAME
    candidate set yields DIFFERENT choices under different beliefs — recon while a target
    factor is uncertain, exploit once the belief is confident. This replaces the
    deterministic PTG next-node pick; the Role wiring falls back to the topo pick on any
    failure (never breaks a run — the free with/without-belief ablation for Phase 3.2).
    """
    cands = list(candidates)
    if not cands:
        raise ValueError("choose_action: no candidate actions.")
    return max(cands, key=lambda a: _action_utility(a, belief))


def run_agent(*args: Any, **kwargs: Any) -> Any:
    """Top-level belief-agent orchestration entry point (R1, TL-2.2 delegator).

    The belief loop lives in `pomdp/agent.py::BeliefAgent` (choose_action → executor.run →
    update_belief → belief_store.save). This function is a thin delegator so the historical
    entry point `belief_state.run_agent(...)` stays valid while the belief MATH in this module
    is untouched. The import is LAZY (inside the function) because `pomdp.agent` imports the
    names in this module — importing it at module load would be a circular import.

    Signature mirrors `pomdp.agent.run_agent(executor, belief_llm, session_id, **kwargs)`:
    the loop-vs-construction kwargs are split there. Returns the final belief.
    """
    from pomdp.agent import run_agent as _run  # lazy: breaks the pomdp.agent ↔ belief_state cycle
    return _run(*args, **kwargs)
