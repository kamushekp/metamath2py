from __future__ import annotations

from typing import List, Optional

from agents import Agent
from pydantic import BaseModel, Field

from saplings.dtos.tasks.patches.patch_set import PatchSetList
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
    instructions = (
        "You are a theorem search specialist. Given a proof task, use the provided "
        "search_tool to fetch relevant theorems/lemmas or examples that could advance "
        "the proof. Return concise summaries/citations that the planner can consume."
    )
    return Agent(
        name="Proof Search Specialist",
        instructions=instructions,
        tools=[search_tool],
    )


def _create_step_planner() -> Agent:
    instructions = (
        "You design the next proof step. Inspect the current proof payload and propose "
        "the single next step as one or more alternative proof_ops (insert). Do not "
        "emit free-form text; focus on appending a valid next step. Collaborate via "
        "handoffs when helpful."
    )
    return Agent(
        name="Proof Step Planner",
        instructions=instructions,
    )


def create_proof_crew_agent() -> Agent:

    search_specialist = _create_search_specialist()
    step_planner = _create_step_planner()

    base_instructions = (
        "You lead a coordinated crew that proves Metamath theorems. The user message is "
        "JSON with top-level keys 'requested_patch_sets' (integer) and 'trajectory'. "
        "'trajectory.initial_task' contains 'goal', 'theorem', and 'proof'. "
        "'theorem' has fields label, floating_args, essential_args, required_theorems "
        "(list of {left, right}), and assertion. 'proof.steps' is an ordered list of "
        "{left, right, comment}. 'trajectory.steps' is an ordered history where each "
        "item has an applied 'patch_set' and resulting 'task_after'. The current state "
        "is already reflected in the last task_after; do not duplicate previous updates. "
        "Generate up to 'requested_patch_sets' alternative PatchSet candidates that each "
        "propose only the next proof step (e.g., if 10 steps exist, return three variants "
        "for step 11, not steps 11–13). Respond strictly with a PatchSetList "
        "{\"patch_sets\": [PatchSet, ...]}. Each PatchSet needs a concise summary and "
        "proof_ops/theorem_ops matching the schema. Avoid returning identical PatchSets. "
        "Default to proof_ops 'insert' that append the next step; do not remove/replace "
        "existing steps unless absolutely necessary and well-justified. Use search_tool "
        "when you need supporting lemmas/examples and cite findings briefly in the "
        "summary. Aim to reach theorem.assertion without altering provided floating/essential "
        "arguments or required_theorems."
    )


    return Agent(
        name="Proof Crew Orchestrator",
        instructions=base_instructions,
        tools=[search_tool],
        handoffs=[search_specialist, step_planner],
        output_type=PatchSetList,
    )
