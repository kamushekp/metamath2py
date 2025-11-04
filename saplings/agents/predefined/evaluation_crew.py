from __future__ import annotations

from typing import Optional

from agents import Agent

from saplings.agents.predefined.proof_crew import TaskResultPayload
from saplings.tools.metamath_tools import create_verify_proof_tool


def _create_verification_specialist(verify_tool) -> Agent:
    instructions = (
        "You verify generated proof artifacts. When asked, run the verification tool "
        "and summarise the outcome. Return structured metadata describing failures."
    )
    kwargs: dict[str, object] = {
        "name": "Proof Evaluation Verifier",
        "instructions": instructions,
        "tools": [verify_tool],
    }
    return Agent(**kwargs)


def create_evaluation_crew_agent() -> Agent:
    """Builds a crew that inspects a trajectory and returns an evaluated TaskResult."""

    verify_tool = create_verify_proof_tool()
    verifier = _create_verification_specialist(verify_tool)

    instructions = (
        "You evaluate a proof trajectory represented as JSON tasks/results. Analyse the "
        "existing proof state, optionally hand off to the verification specialist to run "
        "`verify_proof`, and return JSON matching TaskResultPayload. Provide a clear summary "
        "of the evaluation, populate evaluation.score (0-10), and include verification details "
        "if you performed checks. Do not modify the proof; only assess its quality and completeness."
    )

    kwargs: dict[str, object] = {
        "name": "Proof Evaluation Crew",
        "instructions": instructions,
        "tools": [verify_tool],
        "handoffs": [verifier],
        "output_type": TaskResultPayload
    }
    return Agent(**kwargs)
