from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from agents import Agent

from saplings.dtos.tasks.generated_patch import PatchSet
from saplings.tools.metamath_tools import search_tool


class TheoremPayload(BaseModel):
    label: Optional[str] = Field(default=None, description="Theorem label, if already assigned.")
    floating_args: List[str] = Field(default_factory=list)
    essential_args: List[str] = Field(default_factory=list)
    essential_theorems: List[str] = Field(default_factory=list)
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


def _create_search_specialist(search_tool) -> Agent:
    instructions = (
        "You are a theorem search specialist. Given a proof task, identify relevant "
        "theorems or lemmas that could advance the proof. Always return concise "
        "summaries and references that another agent can consume."
    )
    kwargs: dict[str, Any] = {
        "name": "Proof Search Specialist",
        "instructions": instructions,
        "tools": [search_tool],
    }
    return Agent(**kwargs)


def _create_step_planner() -> Agent:
    instructions = (
        "You design the next proof step. Carefully inspect the task payload and "
        "decide how to extend the proof steps. Collaborate with specialists via "
        "handoffs when helpful. Produce a high-quality summary that other agents "
        "can follow."
    )
    kwargs: dict[str, Any] = {
        "name": "Proof Step Planner",
        "instructions": instructions,
    }
    return Agent(**kwargs)


def create_proof_crew_agent(
    *,
    instructions: Optional[str] = None,
) -> Agent:
    """
    Creates a multi-agent proof crew agent capable of collaborating on theorem tasks.
    """

    # Base tools shared with the orchestrator

    search_specialist = _create_search_specialist()
    step_planner = _create_step_planner()

    base_instructions = (
        "You lead a coordinated crew that proves Metamath theorems. Each user message "
        "contains JSON under the key 'task' with theorem/proof state. Analyse the task, "
        "optionally hand off to specialists (search, planning), and respond "
        "with JSON matching PatchSet. Prefer returning an atomic JSON Patch under "
        "'patch' that transforms the given task to the next state. Keep proof state consistent "
        "and set terminal=true only when the proof is complete or irrecoverably blocked."
    )

    orchestrator_instructions = (
        base_instructions if instructions is None else f"{base_instructions}\n\n{instructions}"
    )

    kwargs: dict[str, Any] = {
        "name": "Proof Crew Orchestrator",
        "instructions": orchestrator_instructions,
        "tools": [search_tool],
        "handoffs": [search_specialist, step_planner],
        "output_type": PatchSet
    }

    return Agent(**kwargs)
