import traceback
from typing import Any, ClassVar
from pydantic import Field, BaseModel
from actions.plan_summary import PlannerSummary
from actions.planner import Planner
from actions.write_code import WriteCode
from db.models.plan_model import Plan
from db.repository.plan_repository import get_planner_by_id, add_plan_to_db
from db.repository.task_repository import add_task_to_plan
from prompts.prompt import DeepPentestPrompt
from server.chat.chat import _chat
from utils.log_common import build_logger
from utils.progress import emit

logger = build_logger()

class Role(BaseModel):
    name: str
    goal: str
    tools: str
    prompt: ClassVar
    max_interactions: int = 5
    previous_summary: PlannerSummary = Field(default_factory=PlannerSummary)
    planner: Planner = Field(default_factory=Planner)
    chat_counter: int = 0
    plan_chat_id: str = ""
    react_chat_id: str = ""
    plan_error: str = ""  # real reason planning failed (e.g. the LLM 429), surfaced to the CLI
    console: Any = None

    def get_summary(self, history_planner_ids):
        self.previous_summary = PlannerSummary(history_planner_ids=history_planner_ids)
        return self.previous_summary.get_summary()

    def put_message(self, message):
        # Guard: if planning never produced a plan (e.g. a dead DB/LLM aborted _plan), there is
        # nothing to persist. Deref-ing current_plan.tasks here is what turned one failure into a
        # confusing cascade, so bail out quietly instead.
        if self.planner.current_plan is None:
            return
        add_task_to_plan(self.planner.current_plan.tasks)
        # To be implemented in each subclass
        pass

    # ── Belief Store hooks (Phase 2.1) ────────────────────────────────────────
    # Best-effort: a failure here must NEVER break a pentest run. The factored JSON
    # belief b is keyed by the current plan id and persisted per step. The real
    # Bayesian update (update_belief on observation O) is wired in Phase 2.2; for now
    # these instantiate and persist b so the run emits a belief trace.
    def _belief_run_id(self):
        return getattr(self.planner.current_plan, "id", None)

    def _belief_init(self, session):
        try:
            from pomdp.belief_store import BeliefStore
            from pomdp.belief_state import new_belief
            run_id = self._belief_run_id()
            if not run_id:
                return
            store = BeliefStore()
            if store.load_latest(run_id) is None:
                store.save(new_belief(session_id=run_id))
                logger.info(f"belief initialized for run {run_id}")
        except Exception as e:  # noqa: BLE001 - belief is auxiliary, never fatal
            logger.warning(f"belief init skipped: {e}")

    def _belief_llm(self, prompt):
        """Thin str->str wrapper over the project LLM choke point, for Z likelihoods."""
        try:
            resp = _chat(query=prompt, summary=False)
            return resp[0] if isinstance(resp, tuple) else resp
        except Exception as e:  # noqa: BLE001
            logger.warning(f"belief llm call failed: {e}")
            return ""

    def _task_to_action_for(self, task):
        """Map a PTG task to a POMDP Action (type inferred from its instruction text)."""
        from pomdp.belief_state import Action, ActionType
        instr = (getattr(task, "instruction", "") or "")
        low = instr.lower()
        if any(k in low for k in ("privesc", "privilege", "sudo", "suid", "escalat")):
            t = ActionType.PRIVESC
        elif any(k in low for k in ("lateral", "pivot", "pass-the-hash")):
            t = ActionType.LATERAL
        elif any(k in low for k in ("exploit", "metasploit", " msf", "payload", "reverse shell", "cve")):
            t = ActionType.EXPLOIT
        else:
            t = ActionType.RECON
        action = Action(name=(instr[:60] or self.name), type=t, host=None, params={})
        try:  # Phase 2.5: fill value/cost/detection_risk from CVE/ExploitDB priors (best-effort)
            from pomdp.priors import enrich_action
            action = enrich_action(action)
        except Exception as e:  # noqa: BLE001 - priors are advisory, never fatal
            logger.warning(f"priors enrichment skipped: {e}")
        return action

    def _task_to_action(self):
        """Map the current PTG task to a POMDP Action."""
        return self._task_to_action_for(getattr(self.planner.current_plan, "current_task", None))

    def _belief_choose_next(self, ready_tasks):
        """Policy hook (Phase 2.4): let the belief pick among dependency-ready tasks.

        Returns the chosen Task, or None to fall back to the deterministic topo pick.
        Env `OCTOPUS_BELIEF_POLICY=0` disables it (the free with/without-belief ablation).
        Best-effort: any failure returns None so the run is never broken.
        """
        try:
            import os
            if os.environ.get("OCTOPUS_BELIEF_POLICY", "1") == "0":
                return None
            from pomdp.belief_store import BeliefStore
            from pomdp.belief_state import choose_action
            run_id = self._belief_run_id()
            if not run_id:
                return None
            b = BeliefStore().load_latest(run_id)
            if b is None:
                return None
            actions = [self._task_to_action_for(t) for t in ready_tasks]
            chosen = choose_action(actions, b)
            self._emit_decision(chosen)  # human-friendly "why this task" line in the CLI
            return ready_tasks[actions.index(chosen)]
        except Exception as e:  # noqa: BLE001 - belief is auxiliary, never fatal
            logger.warning(f"belief task selection skipped: {e}")
            return None

    def _emit_decision(self, action):
        """Stream the policy's pick (π) as a `decision` marker so the CLI can show, in plain
        language, WHY the agent chose this next action — recon to resolve uncertainty (info-gain)
        vs. exploit because the belief says it will pay off. Carries only the chosen action label,
        never hidden state S. Best-effort: a failure here must never break a run."""
        try:
            mode = "recon" if getattr(action, "type", "") == "recon" else "exploit"
            emit("decision", phase=self.name, mode=mode,
                 action=f"{getattr(action, 'type', '?')}:{getattr(action, 'name', '')}"[:60])
        except Exception:  # noqa: BLE001 - progress emission is auxiliary, never fatal
            pass

    def _emit_belief(self, b):
        """Stream the just-updated belief factor as a `belief` marker so the CLI renders the POMDP
        posterior as human-friendly probability bars (not raw JSON). This is the agent's belief —
        its information-state (the posterior over S) — which the thesis exists to surface; it is
        NOT the hidden true state S. Best-effort: a failure here must never break a run."""
        try:
            lu = (b.get("meta") or {}).get("last_update") or {}
            post = lu.get("posterior") or {}
            # encode the distribution as `hyp:prob,hyp:prob` (marker-safe, no `|`)
            dist = ",".join(f"{h}:{float(p):.2f}" for h, p in post.items())
            emit("belief", phase=self.name, step=b.get("step", 0),
                 host=lu.get("host", "?"), factor=lu.get("factor", "?"),
                 key=lu.get("key") or "", action=lu.get("action", "?"), dist=dist)
        except Exception:  # noqa: BLE001 - progress emission is auxiliary, never fatal
            pass

    def _belief_persist(self, observation=""):
        """Belief Updater hook: run the observation O through the soft Bayesian update."""
        try:
            from pomdp.belief_store import BeliefStore
            from pomdp.belief_state import update_belief, z_samples
            run_id = self._belief_run_id()
            if not run_id:
                return
            store = BeliefStore()
            b = store.load_latest(run_id)
            if b is None:
                return
            action = self._task_to_action()
            # self-consistency: average Z over OCTOPUS_Z_SAMPLES calls (TL-2.3), shared with BeliefAgent.
            b = update_belief(b, action, observation, llm=self._belief_llm, samples=z_samples())
            store.save(b)
            self._emit_belief(b)  # surface the updated posterior in the CLI as friendly bars
            logger.info(f"belief updated -> step {b.get('step')}")
        except Exception as e:  # noqa: BLE001 - belief is auxiliary, never fatal
            logger.warning(f"belief persist skipped: {e}")

    def _emit_tasks(self):
        """Stream the current PTG as `task` markers so the CLI can render a live todo checklist.
        Best-effort (belief-style): a formatting/attr error here must never break a run, and the
        markers carry only task boundaries/status — never hidden state S."""
        try:
            tasks = getattr(self.planner.current_plan, "tasks", None) or []
            for t in tasks:
                emit("task", phase=self.name,
                     seq=getattr(t, "sequence", ""),
                     done=int(bool(getattr(t, "is_finished", False))),
                     ok=int(bool(getattr(t, "is_success", False))),
                     instr=(getattr(t, "instruction", "") or "")[:80])
        except Exception:  # noqa: BLE001 - progress emission is auxiliary, never fatal
            pass

    def _react(self, next_task):
        try:
            self.chat_counter += 1
            cur = getattr(self.planner.current_plan, "current_task", None)
            emit("step", phase=self.name, seq=getattr(cur, "sequence", self.chat_counter),
                 instr=(getattr(cur, "instruction", "") or "")[:80])
            writer = WriteCode(next_task=next_task, action=self.planner.current_plan.current_task.action)
            result = writer.run()
            self.console.print("---------- Execute Result ---------", style="bold green")
            logger.info(result.response)
            self.console.print("---------- Execute Result End ---------", style="bold green")
            self.planner.current_plan.current_task.code = result.context["code"]
            self._belief_persist(result.response)   # Phase 2.2: update belief b from observation O
            if len(result.response) >= 8192:
                response, _ = _chat(query=DeepPentestPrompt.summary_result + str(result.response), summary=False)

                logger.info(f"result summary: {response}")
                result.response = response

            next_task = self.planner.update_plan(result.response)
            self._emit_tasks()  # refresh the checklist: update_plan flipped status / merged nodes
            return next_task
        except Exception as e:
            emit("error", phase=self.name, msg=str(e))
            print(e)
            print(traceback.format_exc())

    def _plan(self, session):
        if session.current_planner_id != '':
            self.planner = Planner(current_plan=get_planner_by_id(session.current_planner_id), init_description=session.init_description)
        else:
            with self.console.status("[bold green] Initializing DeepPentest Sessions...") as status:
                try:
                    context = self.get_summary(session.history_planner_ids)
                    # _chat returns (text, chat_id) on success but a bare error *string* on failure;
                    # unpacking that string is what raised "too many values to unpack". Validate first.
                    r0 = _chat(
                        query=self.prompt.init_plan_prompt.format(init_description=session.init_description,
                                                                  goal=self.goal,
                                                                  tools=self.tools,
                                                                  context=context)
                    )
                    if not isinstance(r0, tuple):
                        raise RuntimeError(str(r0))
                    (text_0, self.plan_chat_id) = r0
                    r1 = _chat(query=self.prompt.init_reasoning_prompt)
                    if not isinstance(r1, tuple):
                        raise RuntimeError(str(r1))
                    (text_1, self.react_chat_id) = r1
                except Exception as e:
                    self.plan_error = str(e)  # real cause (e.g. the LLM 429), surfaced to the CLI
                    self.console.print(f"Failed to initialize chat sessions: {e}", style="bold red")
                    return None
            plan = Plan(goal=self.goal, plan_chat_id=self.plan_chat_id, react_chat_id=self.react_chat_id, current_task_sequence=0)
            plan = add_plan_to_db(plan)
            self.console.print("Plan Initialized.", style="bold green")
            session.current_planner_id = plan.id
            self.planner = Planner(current_plan=plan, init_description=session.init_description)

        self._belief_init(session)   # Phase 2.1: instantiate + persist belief b (keyed by plan id)
        self.planner.task_selector = self._belief_choose_next  # Phase 2.4: belief drives the PTG pick
        return self.planner.plan()

    def run(self, session):
        emit("phase", name=self.name)
        next_task = self._plan(session)
        # _plan returns None and leaves current_plan unset when session init fails (dead DB/LLM).
        # Abort cleanly here rather than entering the react loop with a null plan (which used to
        # raise 'NoneType has no attribute current_task' / 'tasks').
        if self.planner.current_plan is None:
            reason = self.plan_error or "planning failed (no plan created)"
            emit("error", phase=self.name, msg=reason)
            emit("phase_done", name=self.name)
            self.console.print(
                f"Aborting run: planning failed - {reason}. Check MySQL/LLM connectivity.",
                style="bold red",
            )
            return
        emit("plan", phase=self.name, tasks=len(getattr(self.planner.current_plan, "tasks", []) or []))
        self._emit_tasks()  # seed the CLI todo checklist with the initial PTG
        while self.chat_counter < self.max_interactions:
            next_task = self._react(next_task)
            if next_task is None:
                break
        emit("phase_done", name=self.name)
        self.put_message(session)