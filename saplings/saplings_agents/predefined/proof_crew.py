from __future__ import annotations

import os

from agents import Agent, ModelSettings

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    PROOF_ORCHESTRATOR_INSTRUCTIONS,
)
from saplings.tools.metamath_tools import search_tool, verify_tool


def create_proof_crew_agent(model: str | None = None) -> Agent:
    selected_model = (model or os.getenv("SAPLINGS_PROOF_CREW_MODEL") or "gpt-5.2").strip()
    model_settings = ModelSettings(
        # Let the model decide when tools are needed to avoid tool-call loops.
        tool_choice="auto",
    )
    return Agent(
        name="Proof Crew Orchestrator",
        instructions=PROOF_ORCHESTRATOR_INSTRUCTIONS,
        model=selected_model,
        tools=[search_tool, verify_tool],
        output_type=PatchSetList,
        model_settings=model_settings,
        # Keep default behavior; forcing repeated tool calls can cause dead loops on early drafts.
        reset_tool_choice=True,
    )
