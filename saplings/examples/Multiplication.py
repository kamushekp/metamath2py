from typing import Annotated, Dict, Any

from agents import function_tool


@function_tool
async def multiply(
    a: Annotated[float, "The number to multiply."],
    b: Annotated[float, "The number to multiply by."],
) -> Dict[str, Any]:
    """Multiplies two numbers and returns the inputs and product."""
    return {"a": a, "b": b, "result": a * b}
