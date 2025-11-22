from __future__ import annotations

from typing import Any, List, Optional

from agents import Runner

from database.opensearch_wrapper import TheoremSearchClient
from saplings.saplings_agents.factories import serialize_trajectory_for_runner
from saplings.saplings_agents.predefined import TaskResultPayload, create_proof_crew_agent
from saplings.dtos.node import Node
from saplings.dtos.tasks.patch import PatchSet, apply_patch
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.task_result import TaskResult
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.dtos.trajectory_step import TrajectoryStep


class CandidateGenerator:

    def __init__(
        self,
        theorem_search_client: TheoremSearchClient,
        b_factor: int = 1,
        step_max_turns: int = 1,
    ):
        self._theorem_search_client = theorem_search_client
        self.b_factor = b_factor
        self.step_max_turns = step_max_turns

    def generate(
        self,
        node: Node,
        prefix_steps: Optional[List[TrajectoryStep]] = None,
        **_: Any,
    ) -> List[TaskTransition]:
        history = self._build_history(node, prefix_steps)
        agent = self._build_agent(history)
        runner_input = self._prepare_runner_input(history)

        transitions: List[TaskTransition] = []
        seen: set[tuple[Any, ...]] = set()

        run_result = Runner.run_sync(
            agent,
            input=runner_input
        )

        payload = run_result.final_output_as(TaskResultPayload)
        task_result = self.payload_to_task_result(payload)
        transition = self._build_transition(node, task_result)

        if not transition:
            return transitions

        key = transition.to_candidate_key()
        if key not in seen:
            seen.add(key)
            transitions.append(transition)
        return transitions

    def _build_prompt(self, history) -> str:
        return ''

    def _build_agent(self, history: List[TrajectoryStep]) -> Any:
        return create_proof_crew_agent(
            theorem_search_client=self._theorem_search_client,
            instructions=self._build_prompt(history),
        )

    def _build_history(
        self, node: Node, prefix_steps: Optional[List[TrajectoryStep]]
    ) -> List[TrajectoryStep]:
        return list(prefix_steps or []) + node.get_trajectory()

    def _prepare_runner_input(self, history: List[TrajectoryStep]) -> List[Any]:
        if not history:
            return []

        return serialize_trajectory_for_runner(history)

    def payload_to_task_result(self, payload: TaskResultPayload) -> TaskResult:
        patch = None
        if getattr(payload, "patch", None):
            patch_items = [p.model_dump() for p in payload.patch]  # type: ignore[attr-defined]
            patch = PatchSet.from_list(patch_items)
        return TaskResult(
            summary=payload.summary,
            patch=patch,
            used_theorems=list(payload.used_theorems),
            terminal=payload.terminal,
        )

    def _build_transition(self, node: Node, result: TaskResult) -> TaskTransition:
        task_dict = node.task.to_dict()
        patched = apply_patch(task_dict, result.patch)
        next_task = Task.from_dict(patched)
        return TaskTransition(task=next_task, result=result)
