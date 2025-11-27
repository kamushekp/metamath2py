from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional

from agents import Runner

from saplings.dtos.node import Node
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.tasks.patches.patch_set import PatchSet, PatchSetList
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.saplings_agents.predefined.proof_crew import create_proof_crew_agent


class CandidateGenerator:

    def _task_to_dict(self, task: CreateNodeTask) -> dict[str, Any]:
        return {
            "goal": task.goal,
            "theorem": {
                "label": task.theorem.label,
                "floating_args": task.theorem.floating_args,
                "essential_args": task.theorem.essential_args,
                "required_theorems":[{'left': t.left, 'right': t.right} for t in task.theorem.required_theorems],
                "assertion": task.theorem.assertion,
            },
            "proof": {
                "steps": [
                    {
                        "left": step.left,
                        "right": step.right,
                        "comment": step.comment,
                    }
                    for step in task.proof.steps
                ],
            },
        }

    def _patch_set_to_dict(self, patch_set: Optional[PatchSet]) -> Optional[dict[str, Any]]:
        if patch_set is None:
            return None

        return {
            "summary": patch_set.summary,
            "theorem_ops": [
                {
                    "field": op.field,
                    "operation": op.operation,
                    "content": op.content,
                    "index": op.index,
                }
                for op in patch_set.theorem_ops
            ],
            "proof_ops": [
                {
                    "operation": op.operation,
                    "left": op.left,
                    "right": op.right,
                    "comment": op.comment,
                }
                for op in patch_set.proof_ops
            ],
        }

    def _format_trajectory(self, node: Node) -> dict[str, Any]:
        transitions = node.get_trajectory()
        initial_task = (
            self._task_to_dict(transitions[0].task_before)
            if transitions
            else self._task_to_dict(node.created_node_task)
        )
        steps = [
            {
                "patch_set": self._patch_set_to_dict(transition.patch_set),
                "task_after": self._task_to_dict(transition.task_after),
            }
            for transition in transitions
        ]
        return {"initial_task": initial_task, "steps": steps}

    def generate(self, node: Node, requested_patch_sets: int = 3) -> Iterable[TaskTransition]:
        agent = create_proof_crew_agent()
        runner_input_obj = {"requested_patch_sets": requested_patch_sets, "trajectory": self._format_trajectory(node)}
        runner_input = json.dumps(runner_input_obj, indent=2)

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
