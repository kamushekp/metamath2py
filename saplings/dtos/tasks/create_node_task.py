from __future__ import annotations

from dataclasses import dataclass

from saplings.dtos.proof_state import ProofState
from saplings.dtos.theorem_state import TheoremState


@dataclass
class CreateNodeTask:
    goal: str
    theorem: TheoremState
    proof: ProofState
    next_step_ideas: str
