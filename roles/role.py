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
    console: Any = None

    def get_summary(self, history_planner_ids):
        self.previous_summary = PlannerSummary(history_planner_ids=history_planner_ids)
        return self.previous_summary.get_summary()

    def put_message(self, message):
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

    def _task_to_action(self):
        """Map the current PTG task to a POMDP Action (type inferred from its text)."""
        from pomdp.belief_state import Action, ActionType
        task = getattr(self.planner.current_plan, "current_task", None)
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
        return Action(name=(instr[:60] or self.name), type=t, host=None, params={})

    def _belief_persist(self, observation=""):
        """Belief Updater hook: run the observation O through the soft Bayesian update."""
        try:
            from pomdp.belief_store import BeliefStore
            from pomdp.belief_state import update_belief
            run_id = self._belief_run_id()
            if not run_id:
                return
            store = BeliefStore()
            b = store.load_latest(run_id)
            if b is None:
                return
            action = self._task_to_action()
            b = update_belief(b, action, observation, llm=self._belief_llm, samples=1)
            store.save(b)
            logger.info(f"belief updated -> step {b.get('step')}")
        except Exception as e:  # noqa: BLE001 - belief is auxiliary, never fatal
            logger.warning(f"belief persist skipped: {e}")

    def _react(self, next_task):
        try:
            self.chat_counter += 1
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

            return self.planner.update_plan(result.response)
        except Exception as e:
            print(e)
            print(traceback.format_exc())

    def _plan(self, session):
        if session.current_planner_id != '':
            self.planner = Planner(current_plan=get_planner_by_id(session.current_planner_id), init_description=session.init_description)
        else:
            with self.console.status("[bold green] Initializing DeepPentest Sessions...") as status:
                try:
                    context = self.get_summary(session.history_planner_ids)
                    (text_0, self.plan_chat_id) = _chat(
                        query=self.prompt.init_plan_prompt.format(init_description=session.init_description,
                                                                  goal=self.goal,
                                                                  tools=self.tools,
                                                                  context=context)
                    )
                    (text_1, self.react_chat_id) = _chat(query=self.prompt.init_reasoning_prompt)
                except Exception as e:
                    self.console.print(f"Failed to initialize chat sessions: {e}", style="bold red")
                    return None
            plan = Plan(goal=self.goal, plan_chat_id=self.plan_chat_id, react_chat_id=self.react_chat_id, current_task_sequence=0)
            plan = add_plan_to_db(plan)
            self.console.print("Plan Initialized.", style="bold green")
            session.current_planner_id = plan.id
            self.planner = Planner(current_plan=plan, init_description=session.init_description)

        self._belief_init(session)   # Phase 2.1: instantiate + persist belief b (keyed by plan id)
        return self.planner.plan()

    def run(self, session):
        next_task = self._plan(session)
        while self.chat_counter < self.max_interactions:
            next_task = self._react(next_task)
            if next_task is None:
                break
        self.put_message(session)