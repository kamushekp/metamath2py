from __future__ import annotations

from typing import Any, List, Optional, Iterable

from agents import Runner

from saplings.dtos.node import Node
from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.saplings_agents.factories import serialize_trajectory_for_runner
from saplings.saplings_agents.predefined import create_proof_crew_agent


class CandidateGenerator:

    def generate(self, node: Node) -> Iterable[TaskTransition]:
        history = self._build_history(node)
        agent = self._build_agent(history)
        runner_input = self._prepare_runner_input(history)

        transitions: List[TaskTransition] = []

        run_result = Runner.run_sync(
            agent,
            input=runner_input
        )

        generated = run_result.final_output_as(PatchSetList)

        for patch_set in generated.patch_sets:
            next_task = patch_set.apply(node.task)
            transitions.append(TaskTransition(node.task, patch_set, next_task))

        seen = set()
        for transition in transitions:
            key = transition.to_candidate_key()
            if key not in seen:
                seen.add(key)
                yield transition
            else:
                print('already seen')

    def _build_prompt(self, history) -> str:
        return ''

    def _build_agent(self, history: List[TaskTransition]) -> Any:
        return create_proof_crew_agent(
            instructions=self._build_prompt(history),
        )

    def _build_history(self, node: Node) -> List[TaskTransition]:
        return list(prefix_steps or []) + node.get_trajectory()

    def _prepare_runner_input(self, history: List[TaskTransition]) -> List[Any]:
        if not history:
            return []

        return serialize_trajectory_for_runner(history)