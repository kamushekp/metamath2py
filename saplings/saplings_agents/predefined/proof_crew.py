from __future__ import annotations

from agents import Agent

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    PROOF_ORCHESTRATOR_INSTRUCTIONS,
    PROOF_SEARCH_INSTRUCTIONS,
    PROOF_STEP_PLANNER_INSTRUCTIONS,
    VALIDATION_AGENT_INSTRUCTIONS,
)
from saplings.tools.metamath_tools import search_tool
from saplings.tools.metamath_tools import verify_tool


def _create_search_specialist() -> Agent:
    instructions = PROOF_SEARCH_INSTRUCTIONS
    return Agent(
        name="Proof Search Specialist",
        instructions=instructions,
        tools=[search_tool],
    )


def _create_step_planner() -> Agent:
    instructions = PROOF_STEP_PLANNER_INSTRUCTIONS
    return Agent(
        name="Proof Step Planner",
        instructions=instructions,
    )


def create_validation_agent() -> Agent:
    """Builds an agent that validates theorem/proof pairs via verify_tool."""

    return Agent(
        name="Proof Validation Agent",
        instructions=VALIDATION_AGENT_INSTRUCTIONS,
        tools=[verify_tool],
    )


def create_proof_crew_agent() -> Agent:

    search_specialist = _create_search_specialist()
    step_planner = _create_step_planner()

    base_instructions = PROOF_ORCHESTRATOR_INSTRUCTIONS

    return Agent(
        name="Proof Crew Orchestrator",
        instructions=base_instructions,
        handoffs=[search_specialist, step_planner],
        output_type=PatchSetList,
    )
