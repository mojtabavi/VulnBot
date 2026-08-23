import json
from typing import Any, Callable, List, Optional

from pydantic import BaseModel

from actions.write_plan import WritePlan, parse_tasks, merge_tasks
from config.config import Configs
from db.models.task_model import TaskModel, Task
from prompts.prompt import DeepPentestPrompt
from db.models.plan_model import Plan
from server.chat.chat import _chat
from utils.log_common import build_logger

logger = build_logger()


class Planner(BaseModel):
    current_plan: Plan = None
    init_description: str = ""
    # Belief-conditioned selection (Phase 2.4): optional callable ready_tasks -> chosen Task.
    # Set by the Role from its belief hooks; None = deterministic PTG pick (unchanged behavior).
    task_selector: Optional[Any] = None

    def plan(self):
        if self.current_plan.current_task:
            next_task = self.next_task_details()
            return next_task

        response = WritePlan(plan_chat_id=self.current_plan.plan_chat_id).run(self.init_description)

        logger.info(f"plan: {response}")

        try:
            self.current_plan = parse_tasks(response, self.current_plan)
        except (ValueError, json.JSONDecodeError) as e:
            # No usable task JSON (dead/unsupported LLM). Null the plan so Role.run's guard aborts
            # cleanly with one message, instead of crashing on json.loads / a null current_task.
            logger.error(f"planning failed: {e}")
            self.current_plan = None
            return None

        next_task = self.next_task_details()

        return next_task

    def update_plan(self, result):

        check_success = _chat(
            query=DeepPentestPrompt.check_success.format(result=result),
            conversation_id=self.current_plan.react_chat_id
        )

        logger.info(f"check_success: {check_success}")

        if "yes" in check_success.lower():
            task_result = self.update_task_status(self.current_plan.id, self.current_plan.current_task_sequence,
                                                  True, True, result)
        else:
            task_result = self.update_task_status(self.current_plan.id, self.current_plan.current_task_sequence,
                                                  True, False, result)

        # 更新
        updated_response = (WritePlan(plan_chat_id=self.current_plan.plan_chat_id)
                            .update(task_result,
                                    self.current_plan.finished_success_tasks,
                                    self.current_plan.finished_fail_tasks,
                                    self.init_description))

        logger.info(f"updated_plan: {updated_response}")

        if updated_response == "" or updated_response is None:
            return None

        merge_tasks(updated_response, self.current_plan)

        next_task = self.next_task_details()

        return next_task

    def next_task_details(self):
        logger.info(f"current_task: {self.current_plan.current_task}")
        current = self.current_plan.current_task
        if current is None:
            return None

        # Phase 2.4 — belief-conditioned pick among the dependency-ready frontier.
        # Guarded: any failure (or no selector) falls back to the deterministic topo pick,
        # so a belief problem NEVER breaks a run and the ablation (3.2) is a free toggle.
        if self.task_selector is not None:
            try:
                ready = self.current_plan.ready_tasks
                if len(ready) > 1:
                    chosen = self.task_selector(ready)
                    if chosen is not None:
                        current = chosen
                        logger.info(f"belief-selected task: seq={current.sequence} {current.instruction!r}")
            except Exception as e:  # noqa: BLE001 - belief is auxiliary, never fatal
                logger.warning(f"belief task selection skipped: {e}")

        self.current_plan.current_task_sequence = current.sequence
        next_task = _chat(
            query=DeepPentestPrompt.next_task_details.format(todo_task=current.instruction),
            conversation_id=self.current_plan.react_chat_id,
            kb_name=Configs.kb_config.kb_name,
            kb_query=current.instruction
        )
        return next_task

    def update_task_status(self, plan_id: str, task_sequence: int,
                           is_finished: bool, is_success: bool, result: Optional[str] = None) -> Task:
        """更新任务状态"""

        task = next((
            task for task in self.current_plan.tasks
            if task.plan_id == plan_id and task.sequence == task_sequence
        ), None)

        if task:
            task.is_finished = is_finished
            task.is_success = is_success
            if result:
                task.result = result

        # 返回更新后的计划
        return task
