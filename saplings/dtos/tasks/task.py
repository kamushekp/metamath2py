from __future__ import annotations

from dataclasses import dataclass

from saplings.dtos.proof import ProofState, TheoremState


@dataclass
class Task:
    goal: str
    theorem: TheoremState
    proof: ProofState