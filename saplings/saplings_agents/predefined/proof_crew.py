from __future__ import annotations

from agents import Agent, ModelSettings

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    PROOF_ORCHESTRATOR_INSTRUCTIONS,
)
from saplings.tools.metamath_tools import search_tool, verify_tool


def create_proof_crew_agent() -> Agent:
    model_settings = ModelSettings(
        # Require a tool call every turn while keeping all tools available.
        tool_choice="required",
    )
    return Agent(
        name="Proof Crew Orchestrator",
        instructions=PROOF_ORCHESTRATOR_INSTRUCTIONS,
        tools=[search_tool, verify_tool],
        output_type=PatchSetList,
        model_settings=model_settings,
        # Keep tool_choice enforced even after the first tool call; we want repeated verification.
        reset_tool_choice=False,
    )
