from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from saplings.dtos.Proof import ProofState, TheoremState


@dataclass
class Task:
    """Represents a single unit of work for the proof search agent."""

    goal: str
    theorem: Optional[TheoremState] = None
    proof: Optional[ProofState] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "goal": self.goal,
        }
        if self.theorem is not None:
            data["theorem"] = self.theorem.to_dict()
        if self.proof is not None:
            data["proof"] = self.proof.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        obj = cls(
            goal=data.get("goal", ""),
        )
        if "theorem" in data:
            obj.theorem = TheoremState.from_dict(data["theorem"])  # type: ignore[arg-type]
        if "proof" in data:
            obj.proof = ProofState.from_dict(data["proof"])  # type: ignore[arg-type]
        return obj

    @classmethod
    def from_goal(
        cls,
        goal: str,
        *,
        theorem: Optional[TheoremState] = None,
        proof: Optional[ProofState] = None,
    ) -> "Task":
        return cls(
            goal=goal,
            theorem=theorem,
            proof=proof,
        )
