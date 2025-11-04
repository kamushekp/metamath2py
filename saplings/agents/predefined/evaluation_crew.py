from __future__ import annotations

from typing import Any, Optional, Sequence

from saplings.agents.factories import create_agent
from saplings.agents.predefined.proof_crew import TaskResultPayload
from saplings.tools.metamath_tools import create_verify_proof_tool


def _create_verification_specialist(verify_tool) -> Any:
    instructions = (
        "You verify generated proof artifacts. When asked, run the verification tool "
        "and summarise the outcome. Return structured metadata describing failures."
    )
    return create_agent(
        name="Proof Evaluation Verifier",
        instructions=instructions,
        tools=[verify_tool],
        temperature=0.0,
    )


def create_evaluation_crew_agent(
    *,
    model_name: Optional[str] = None,
    max_output_tokens: int = 1536,
    temperature: float = 0.0,
    parallel_tool_calls: bool = False,
    extra_tools: Sequence[Any] | None = None,
) -> Any:
    """Builds a crew that inspects a trajectory and returns an evaluated TaskResult."""

    verify_tool = create_verify_proof_tool()
    specialists = [_create_verification_specialist(verify_tool)]

    instructions = (
        "You evaluate a proof trajectory represented as JSON tasks/results. Analyse the"
        " existing proof state, optionally hand off to the verification specialist to"
        " run `verify_proof`, and return JSON matching TaskResultPayload. Provide a"
        " clear summary of the evaluation, populate evaluation.score (0-10), and include"
        " verification details if you performed checks. Do not modify the proof; only"
        " assess its quality and completeness."
    )

    tools = [verify_tool]
    if extra_tools:
        tools.extend(extra_tools)

    return create_agent(
        name="Proof Evaluation Crew",
        instructions=instructions,
        model_name=model_name,
        tools=tools,
        handoffs=specialists,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        parallel_tool_calls=parallel_tool_calls,
        output_type=TaskResultPayload,
    )
