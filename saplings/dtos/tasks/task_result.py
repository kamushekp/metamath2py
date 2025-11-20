from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from saplings.dtos.evaluations.verification_outcome import VerificationOutcome
from saplings.dtos.evaluations.evaluation import Evaluation
from saplings.dtos.tasks.patch import PatchSet


@dataclass
class TaskResult:
    """Represents the outcome produced by the agent crew for a task."""

    summary: str
    patch: Optional[PatchSet] = None
    used_theorems: List[str] = field(default_factory=list)
    verification: Optional[VerificationOutcome] = None
    evaluation: Optional[Evaluation] = None
    terminal: bool = False
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "patch": [vars(op) for op in self.patch.ops] if self.patch else None,
            "used_theorems": list(self.used_theorems),
            "verification": self.verification.to_dict() if self.verification else None,
            "evaluation": {
                "score": self.evaluation.score,
                "reasoning": self.evaluation.reasoning,
            }
            if self.evaluation
            else None,
            "terminal": bool(self.terminal),
            "artifacts": dict(self.artifacts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TaskResult":
        evaluation_payload = payload.get("evaluation")
        evaluation = None
        if evaluation_payload:
            evaluation = Evaluation(
                score=evaluation_payload.get("score", 0.0),
                reasoning=evaluation_payload.get("reasoning"),
            )
        verification_payload = payload.get("verification")
        verification = (
            VerificationOutcome.from_dict(verification_payload)
            if verification_payload
            else None
        )
        patch_payload = payload.get("patch")
        patch = PatchSet.from_list(patch_payload) if patch_payload else None

        return cls(
            summary=payload.get("summary", ""),
            used_theorems=list(payload.get("used_theorems", [])),
            patch=patch,
            verification=verification,
            evaluation=evaluation,
            terminal=bool(payload.get("terminal", False)),
            artifacts=dict(payload.get("artifacts", {})),
            metadata=dict(payload.get("metadata", {})),
        )


