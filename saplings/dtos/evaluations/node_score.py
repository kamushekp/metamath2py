from __future__ import annotations

from dataclasses import dataclass

from saplings.dtos.evaluations.evaluation import Evaluation


@dataclass
class NodeScore(Evaluation):
    """Numeric score for a Node plus textual reasoning."""

    depth: int = 0
    verify_progress: float = 0.0
    structural_progress: float = 0.0
    stage: str = ""


