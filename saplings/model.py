from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Iterable, List, Optional

from openai import AsyncOpenAI

try:
    from saplings.dtos import Message
    from saplings.abstract import Tool
except ImportError:
    from dtos import Message
    from abstract import Tool


_DEFAULT_CONTEXT_WINDOW = 128_000


def _message_to_input_items(message: Message) -> List[dict[str, Any]]:
    items: List[dict[str, Any]] = []

    if message.role == "tool":
        call_id = message.tool_call_id or ""
        items.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": message.content or "",
            }
        )
        return items

    if message.content is not None:
        items.append(
            {
                "type": "message",
                "role": message.role,
                "content": message.content,
            }
        )

    if message.tool_calls:
        for tool_call in message.tool_calls:
            call_id = getattr(tool_call, "id", None) or getattr(tool_call, "name", "")
            arguments = getattr(tool_call, "arguments", {})
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments)

            items.append(
                {
                    "type": "function_call",
                    "id": call_id,
                    "call_id": call_id,
                    "name": getattr(tool_call, "name", ""),
                    "arguments": arguments,
                }
            )

    if not items:
        items.append(
            {
                "type": "message",
                "role": message.role,
                "content": message.content or "",
            }
        )

    return items


def _serialize_messages_for_responses(messages: Iterable[Message]) -> List[dict[str, Any]]:
    serialized: List[dict[str, Any]] = []
    for message in messages:
        serialized.extend(_message_to_input_items(message))
    return serialized


def _response_to_openai_message(response: Any) -> SimpleNamespace:
    payload = response.to_dict() if hasattr(response, "to_dict") else response
    output_items = payload.get("output") or []

    text_parts: List[str] = []
    tool_calls: List[SimpleNamespace] = []

    for item in output_items:
        item_type = item.get("type")
        if item_type == "message":
            for content in item.get("content") or []:
                if content.get("type") == "output_text":
                    text_parts.append(content.get("text") or "")
        elif item_type == "function_call":
            tool_calls.append(
                SimpleNamespace(
                    id=item.get("id") or item.get("call_id"),
                    function=SimpleNamespace(
                        name=item.get("name"),
                        arguments=item.get("arguments"),
                    ),
                )
            )

    content = "".join(text_parts) if text_parts else None
    return SimpleNamespace(role="assistant", content=content, tool_calls=tool_calls or None)


class _Choice:
    def __init__(self, index: int, message: SimpleNamespace) -> None:
        self.index = index
        self.message = message


class Model(object):
    def __init__(
        self,
        model: str,
        client: Optional[AsyncOpenAI] = None,
        *,
        context_window: int = _DEFAULT_CONTEXT_WINDOW,
        **client_kwargs: Any,
    ):
        self.model = model
        self._context_window = context_window
        self._client = client or AsyncOpenAI(**client_kwargs)

    def get_context_window(self) -> int:
        return self._context_window

    def count_tokens(self, text: str) -> int:
        return 0

    def count_message_tokens(self, message: Message) -> int:
        return 0

    def count_tool_tokens(self, tool: Tool) -> int:
        return 0

    def truncate_messages(
        self, messages: list[Message], headroom: int, tools: list[Tool] | None = None
    ) -> list[Message]:
        return list(messages)

    async def run_async(
        self,
        messages: list[Message],
        stream: bool = False,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        n: Optional[int] = None,
        tools: Optional[Iterable[dict[str, Any]]] = None,
        tool_choice: Any = None,
        parallel_tool_calls: Optional[bool] = None,
        response_format: Optional[dict[str, Any]] = None,
        **request_options: Any,
    ) -> Any:
        del frequency_penalty, presence_penalty  # Unused in new API

        payload: dict[str, Any] = {
            "model": self.model,
            "input": _serialize_messages_for_responses(messages),
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens
        if parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = parallel_tool_calls
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format and response_format != {"type": "text"}:
            payload["text"] = {"format": response_format}

        request_kwargs = {
            key: request_options.pop(key)
            for key in ("extra_headers", "extra_query", "extra_body", "timeout")
            if key in request_options
        }

        if request_options:
            payload.update(request_options)

        if stream:
            return self._client.responses.stream(**payload, **request_kwargs)

        result_count = max(1, n or 1)
        if result_count == 1:
            response = await self._client.responses.create(**payload, **request_kwargs)
            return _response_to_openai_message(response)

        choices: List[_Choice] = []
        for index in range(result_count):
            response = await self._client.responses.create(**payload, **request_kwargs)
            choices.append(_Choice(index, _response_to_openai_message(response)))
        return choices
