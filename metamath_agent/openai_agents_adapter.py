from __future__ import annotations

"""Optional adapters to interop with OpenAI Agents SDK (Python).

This module provides thin wrappers that convert Saplings tools into
OpenAI Agents SDK function tools when the `openai-agents-python` package
is installed. The adapters are imported lazily to avoid a hard dependency.

Docs reference: /websites/openai_github_io_openai-agents-python (via Context7)
Key concepts: Agents, Sessions, Function tools, Handoffs.
"""

from typing import Any, List

try:  # pragma: no cover - optional
    # The concrete import path may vary by version; try common names.
    from agents import FunctionTool  # type: ignore
except Exception:  # pragma: no cover
    FunctionTool = None  # type: ignore


def saplings_tool_to_function_tool(tool) -> Any:
    """Convert a Saplings Tool into an OpenAI Agents `FunctionTool`.

    Returns a `FunctionTool` instance if the SDK is available, otherwise raises
    ImportError with guidance.
    """

    if FunctionTool is None:
        raise ImportError(
            "openai-agents-python is not installed. Install it to enable Agents SDK interop."
        )

    async def on_invoke_tool(ctx, args):  # noqa: ANN001 - SDK-defined signature
        # Saplings `run` expects kwargs
        result = await tool.run(**args)
        # Agents SDK expects string outputs for Realtime tool output
        return tool.format_output(result)

    return FunctionTool(
        tool_name=tool.name,
        tool_description=tool.description,
        parameters_schema=tool.parameters,
        on_invoke_tool=on_invoke_tool,
    )


def saplings_tools_to_function_tools(tools: List[Any]) -> List[Any]:
    return [saplings_tool_to_function_tool(t) for t in tools]

