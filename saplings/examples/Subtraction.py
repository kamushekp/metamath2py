from typing import Annotated

from agents import function_tool


@function_tool
async def subtract(
    a: Annotated[float, "The number to subtract from."],
    b: Annotated[float, "The number you're subtracting."],
) -> float:
    """Subtracts two numbers and returns the difference."""
    return a - b
