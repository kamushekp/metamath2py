from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence

from agents import Agent as OAAgent, ModelSettings

from saplings.dtos import Message


def create_agent(
    *,
    name: str,
    instructions: str,
    tools: Sequence[Any] | None = None,
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

    extra_args = {"parallel_tool_calls": parallel_tool_calls}
    if extra_model_args:
        extra_args.update(extra_model_args)

    model_settings = ModelSettings(
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        extra_args=extra_args,
    )

    kwargs: dict[str, Any] = {
        "name": name,
        "instructions": instructions,
        "model_settings": model_settings,
    }
    if tools:
        kwargs["tools"] = list(tools)
    if model_name:
        kwargs["model"] = model_name
    if output_type is not None:
        kwargs["output_type"] = output_type

    return OAAgent(**kwargs)


def _message_to_input_items(message: Message) -> List[dict[str, Any]]:
    if message.content is None:
        return []
    return [
        {
            "type": "message",
            "role": message.role,
            "content": message.content,
        }
    ]


def serialize_messages_for_runner(messages: Iterable[Message]) -> List[dict[str, Any]]:
    """
    Converts Message objects into the Responses API payload used by Runner sessions.
    """

    serialized: List[dict[str, Any]] = []
    for message in messages:
        serialized.extend(_message_to_input_items(message))
    return serialized
