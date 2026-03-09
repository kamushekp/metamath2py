from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from saplings.dtos.evaluations.evaluation import Evaluation
from verification import ProofCheckStage


@dataclass
class NodeScore(Evaluation):
    """Numeric score for a Node plus textual reasoning."""

    depth: int = 0
    verify_progress: float = 0.0
    structural_progress: float = 0.0
    stage: Optional[ProofCheckStage] = None
