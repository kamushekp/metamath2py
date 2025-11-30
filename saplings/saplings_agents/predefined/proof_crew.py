from __future__ import annotations

from agents import Agent

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    PROOF_ORCHESTRATOR_INSTRUCTIONS,
)
from saplings.tools.metamath_tools import search_tool, verify_tool


def create_proof_crew_agent() -> Agent:
    return Agent(
        name="Proof Crew Orchestrator",
        instructions=PROOF_ORCHESTRATOR_INSTRUCTIONS,
        tools=[search_tool, verify_tool],
        output_type=PatchSetList,
    )
