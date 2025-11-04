from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional, Sequence

from agents import Agent as OAAgent, ModelSettings

from saplings.dtos.Node import TrajectoryStep
from saplings.dtos.tasks.Task import Task
from saplings.dtos.tasks.TaskResult import TaskResult


def create_agent(
    *,
    name: str,
    instructions: str,
    tools: Sequence[Any] | None = None,
    handoffs: Sequence[Any] | None = None,
    model_name: Optional[str] = None,
    max_output_tokens: int = 2048,
    temperature: float = 1.0,
    parallel_tool_calls: bool = False,
    extra_model_args: Optional[dict[str, Any]] = None,
    output_type: Any | None = None,
) -> OAAgent:
    """
    Factory helper that creates an OpenAI Agents SDK Agent with consistent defaults.
    """

    model_settings = ModelSettings(
        max_output_tokens=max_output_tokens,
        temperature=temperature
    )

    kwargs: dict[str, Any] = {
        "name": name,
        "instructions": instructions,
        "model_settings": model_settings,
    }
    if tools:
        kwargs["tools"] = list(tools)
    if handoffs:
        kwargs["handoffs"] = list(handoffs)
    if model_name:
        kwargs["model"] = model_name
    if output_type is not None:
        kwargs["output_type"] = output_type

    return OAAgent(**kwargs)


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
