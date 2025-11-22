from __future__ import annotations

from typing import Any, List, Optional

from agents import Runner

from saplings.saplings_agents.factories import serialize_trajectory_for_runner
from saplings.saplings_agents.predefined import create_proof_crew_agent
from saplings.dtos.node import Node
from saplings.dtos.tasks.generated_patch import GeneratedPatch
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.dtos.trajectory_step import TrajectoryStep


class CandidateGenerator:

    def __init__(
        self,
        b_factor: int = 1,
        step_max_turns: int = 1,
    ):
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

        generated = run_result.final_output_as(GeneratedPatch)
        transition = self._build_transition(node, generated)

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

    def _build_transition(self, node: Node, result: GeneratedPatch) -> Optional[TaskTransition]:
        if not result.patch:
            return None
        patched_task = result.patch.apply(node.task)
        return TaskTransition(task=patched_task, result=result)
