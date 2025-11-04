from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents import Agent

from database.opensearch_wrapper import TheoremSearchClient
from saplings.tools.metamath_tools import (
    create_search_theorems_tool,
    create_verify_proof_tool,
)


class SymbolDeclPayload(BaseModel):
    name: str
    sort: Optional[str] = Field(default=None, description="Metamath sort (e.g., wff, setvar).")
    annotation: Dict[str, Any] = Field(default_factory=dict)


class TheoremPayload(BaseModel):
    label: Optional[str] = Field(default=None, description="Theorem label, if already assigned.")
    floating_args: List[SymbolDeclPayload] = Field(default_factory=list)
    essential_args: List[SymbolDeclPayload] = Field(default_factory=list)
    essential_theorems: List[str] = Field(default_factory=list)
    assertion: Optional[str] = Field(default=None)


class ProofStepPayload(BaseModel):
    reference: str = Field(description="Name of the theorem/axiom used in this step.")
    substitutions: Dict[str, Any] = Field(default_factory=dict)
    comment: Optional[str] = Field(default=None)


class ProofPayload(BaseModel):
    steps: List[ProofStepPayload] = Field(default_factory=list)


class EvaluationPayload(BaseModel):
    reasoning: str = Field(
        description="Concise reflection summarizing the trajectory's strengths and weaknesses."
    )
    score: float = Field(
        ge=0,
        le=10,
        description="Quality score between 0 and 10 where 10 means the trajectory fully satisfies the user.",
    )


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


class VerificationPayload(BaseModel):
    success: bool = Field(
        description="True when the generated proof artifacts verify successfully."
    )
    stage: Optional[str] = Field(
        default=None,
        description="If verification fails, identifies the failing pipeline stage.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Concise explanation of the verification failure, if any.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostics such as tracebacks or file paths.",
    )


class TaskResultPayload(BaseModel):
    summary: str = Field(
        description="Human-readable narration of the new proof step that was attempted."
    )
    used_theorems: List[str] = Field(
        default_factory=list,
        description="List of references or theorems used when constructing this step.",
    )
    verification: Optional[VerificationPayload] = Field(
        default=None,
        description="Verification outcome for any generated proof artifacts.",
    )
    evaluation: Optional[EvaluationPayload] = Field(
        default=None,
        description="Self-evaluated quality score (0-10) with reasoning.",
    )
    terminal: bool = Field(
        default=False,
        description="Set to true when the proof is complete or irrecoverably blocked.",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Paths or identifiers of generated files for downstream tooling.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra structured context returned by the crew.",
    )
    patch: Optional[List["JsonPatchOp"]] = Field(
        default=None,
        description="Atomic JSON-Patch operations to transform the current Task into the next state.",
    )


class JsonPatchOp(BaseModel):
    op: str = Field(description="One of add/remove/replace")
    path: str = Field(description="JSON Pointer path to target field")
    value: Any | None = Field(default=None, description="Value for add/replace")


TaskResultPayload.model_rebuild()
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


def _create_verification_specialist(verify_tool) -> Agent:
    instructions = (
        "You verify generated proof artifacts. When asked, run the verification tool "
        "and summarise the outcome. Return structured metadata describing failures."
    )
    kwargs: dict[str, Any] = {
        "name": "Proof Verification Specialist",
        "instructions": instructions,
        "tools": [verify_tool],
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
    theorem_search_client: TheoremSearchClient,
    instructions: Optional[str] = None,
) -> Agent:
    """
    Creates a multi-agent proof crew agent capable of collaborating on theorem tasks.
    """

    # Base tools shared with the orchestrator
    search_tool = create_search_theorems_tool(theorem_search_client)
    verify_tool = create_verify_proof_tool()

    search_specialist = _create_search_specialist(search_tool)
    verification_specialist = _create_verification_specialist(verify_tool)
    step_planner = _create_step_planner()

    base_instructions = (
        "You lead a coordinated crew that proves Metamath theorems. Each user message "
        "contains JSON under the key 'task' with theorem/proof state. Analyse the task, "
        "optionally hand off to specialists (search, verification, planning), and respond "
        "with JSON matching TaskResultPayload. Prefer returning an atomic JSON Patch under "
        "'patch' that transforms the given task to the next state. Keep proof state consistent, update the evaluation "
        "score (0-10), and set terminal=true only when the proof is complete or irrecoverably blocked."
    )

    orchestrator_instructions = (
        base_instructions if instructions is None else f"{base_instructions}\n\n{instructions}"
    )

    kwargs: dict[str, Any] = {
        "name": "Proof Crew Orchestrator",
        "instructions": orchestrator_instructions,
        "tools": [search_tool, verify_tool],
        "handoffs": [search_specialist, verification_specialist, step_planner],
        "output_type": TaskResultPayload
    }

    return Agent(**kwargs)
