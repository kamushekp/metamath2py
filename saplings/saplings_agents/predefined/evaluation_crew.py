from __future__ import annotations

from agents import Agent

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    EVALUATION_CREW_INSTRUCTIONS,
)


def create_evaluation_crew_agent() -> Agent:
    """Builds a crew that inspects a trajectory and returns a PatchSet."""

    instructions = EVALUATION_CREW_INSTRUCTIONS

    return Agent(
        name="Proof Evaluation Crew",
        instructions=instructions,
        output_type=PatchSetList,
    )
