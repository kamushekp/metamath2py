from __future__ import annotations

from dataclasses import dataclass

from saplings.dtos.proof_state import ProofState
from saplings.dtos.theorem_state import TheoremState


@dataclass
class CreateNodeTask:
    goal: str
    theorem: TheoremState
    proof: ProofState
    next_step_ideas: str = ""

    @classmethod
    def from_goal(cls, goal: str) -> "CreateNodeTask":
        """
        Backward-compatible constructor used by older tests.
        """

        return cls(
            goal=goal,
            theorem=TheoremState(
                label="",
                floating_args=[],
                essential_args=[],
                required_theorem_premises=[],
                assertion="",
            ),
            proof=ProofState(steps=[]),
            next_step_ideas="",
        )
