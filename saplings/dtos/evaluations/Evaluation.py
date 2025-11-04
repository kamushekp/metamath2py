from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Evaluation:
    score: float
    reasoning: Optional[str] = None
