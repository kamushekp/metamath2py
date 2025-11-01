from typing import Annotated

from agents import function_tool


@function_tool
async def divide(
    a: Annotated[float, "The numerator."],
    b: Annotated[float, "The denominator."],
) -> float:
    """Divides two numbers and returns the quotient."""
    return a / b
