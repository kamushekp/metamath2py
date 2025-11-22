from __future__ import annotations

from agents import Agent

from saplings.dtos.tasks.generated_patch import GeneratedPatch


def create_evaluation_crew_agent() -> Agent:
    """Builds a crew that inspects a trajectory and returns a GeneratedPatch."""

    instructions = (
        "You evaluate a proof trajectory represented as JSON tasks/results. Analyse the "
        "existing proof state and return JSON matching GeneratedPatch. Provide a clear summary "
        "of the evaluation, and set terminal=true only when the proof is complete or irrecoverably blocked. "
        "Do not modify the proof; only assess its quality and completeness."
    )

    kwargs: dict[str, object] = {
        "name": "Proof Evaluation Crew",
        "instructions": instructions,
        "output_type": GeneratedPatch
    }
    return Agent(**kwargs)
