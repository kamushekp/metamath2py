from __future__ import annotations

from typing import Any, List, Optional, Iterable

from agents import Runner

from saplings.dtos.node import Node
from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.saplings_agents.predefined import create_proof_crew_agent


class CandidateGenerator:

    def generate(self, node: Node) -> Iterable[TaskTransition]:
        trajectory = node.get_trajectory()
        agent = create_proof_crew_agent()
        runner_input = str(trajectory)

        transitions: List[TaskTransition] = []

        run_result = Runner.run_sync(agent, input=runner_input)

        generated = run_result.final_output_as(PatchSetList)

        original_task = node.created_node_task
        for patch_set in generated.patch_sets:
            next_task = patch_set.apply(original_task)
            transitions.append(TaskTransition(original_task, patch_set, next_task))

        seen = set()
        for transition in transitions:
            key = transition.to_candidate_key()
            if key not in seen:
                seen.add(key)
                yield transition
            else:
                print('already seen')
