from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field

from saplings.agents.factories import create_agent
from saplings.tools.metamath_tools import create_verify_proof_tool


class EvaluationPayload(BaseModel):
    reasoning: str = Field(
        description="A concise reflection summarizing the trajectory's strengths and weaknesses."
    )
    score: float = Field(
        ge=0,
        le=10,
        description="Quality score between 0 and 10 where 10 means the trajectory fully satisfies the user.",
    )


def create_evaluator_agent(
    *,
    model_name: Optional[str] = None,
    max_output_tokens: int = 1024,
) -> any:
    """Builds the predefined evaluation agent with verification tooling."""

    instructions = (
        "You evaluate proof trajectories. When a proof module is referenced, use the "
        "verify_proof tool to check it. Respond with JSON containing 'reasoning' and "
        "'score' (0-10)."
    )

    return create_agent(
        name="Saplings Evaluator",
        instructions=instructions,
        model_name=model_name,
        max_output_tokens=max_output_tokens,
        temperature=0.0,
        tools=[create_verify_proof_tool()],
        output_type=EvaluationPayload,
    )
