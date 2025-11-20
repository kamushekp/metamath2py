from __future__ import annotations

import json
from typing import Any, Iterable, List

from saplings.dtos import TrajectoryStep
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.task_result import TaskResult


def _task_to_input_items(task: Task) -> List[dict[str, Any]]:
    payload = {"task": task.to_dict()}
    return [
        {
            "type": "message",
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        }
    ]


def _result_to_input_items(result: TaskResult) -> List[dict[str, Any]]:
    payload = {"result": result.to_dict()}
    return [
        {
            "type": "message",
            "role": "assistant",
            "content": json.dumps(payload, ensure_ascii=False),
        }
    ]


def serialize_trajectory_for_runner(steps: Iterable[TrajectoryStep]) -> List[dict[str, Any]]:
    """
    Converts Task/TaskResult trajectory steps into Responses API payload items.
    """

    serialized: List[dict[str, Any]] = []
    ordered_steps = list(steps)
    if not ordered_steps:
        return serialized

    # Emit the initial task
    serialized.extend(_task_to_input_items(ordered_steps[0].task))

    # For subsequent steps, interleave agent outputs with follow-up tasks.
    for step in ordered_steps[1:]:
        if step.result:
            serialized.extend(_result_to_input_items(step.result))
        serialized.extend(_task_to_input_items(step.task))

    return serialized
