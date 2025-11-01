from typing import Annotated

from agents import function_tool


@function_tool
async def add(
    a: Annotated[float, "The first number to add."],
    b: Annotated[float, "The second number to add."],
) -> float:
    """Adds two numbers and returns the result."""
    return a + b
