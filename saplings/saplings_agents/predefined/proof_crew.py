from __future__ import annotations

from typing import List, Optional

from agents import Agent
from pydantic import BaseModel, Field

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.saplings_agents.predefined.agent_descriptions import (
    PROOF_ORCHESTRATOR_INSTRUCTIONS,
    PROOF_SEARCH_INSTRUCTIONS,
    PROOF_STEP_PLANNER_INSTRUCTIONS,
)
from saplings.tools.metamath_tools import search_tool


class RequiredTheoremPayload(BaseModel):
    left: str = Field(description="Alias/name referenced in the proof steps.")
    right: str = Field(description="Actual theorem content or reference string.")


class TheoremPayload(BaseModel):
    label: Optional[str] = Field(default=None, description="Theorem label, if already assigned.")
    floating_args: List[str] = Field(default_factory=list)
    essential_args: List[str] = Field(default_factory=list)
    required_theorems: List[RequiredTheoremPayload] = Field(default_factory=list)
    assertion: Optional[str] = Field(default=None)


class ProofStepPayload(BaseModel):
    left: str = Field(description="Left-hand expression of the proof step.")
    right: str = Field(description="Right-hand expression of the proof step.")
    comment: Optional[str] = Field(default=None)


class ProofPayload(BaseModel):
    steps: List[ProofStepPayload] = Field(default_factory=list)


class TaskPayload(BaseModel):
    goal: str = Field(description="User-specified theorem proving objective.")
    theorem: Optional[TheoremPayload] = Field(
        default=None,
        description="Structured description of the theorem being constructed.",
    )
    proof: Optional[ProofPayload] = Field(
        default=None,
        description="Current proof state as a sequence of steps.",
    )


TaskPayload.model_rebuild()


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


def create_proof_crew_agent() -> Agent:

    search_specialist = _create_search_specialist()
    step_planner = _create_step_planner()

    base_instructions = PROOF_ORCHESTRATOR_INSTRUCTIONS


    return Agent(
        name="Proof Crew Orchestrator",
        instructions=base_instructions,
        tools=[search_tool],
        handoffs=[search_specialist, step_planner],
        output_type=PatchSetList,
    )
