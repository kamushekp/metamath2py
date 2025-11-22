from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ProofState:
    steps: List[ProofStep]


@dataclass
class ProofStep:
    left: str
    right: str
    comment: Optional[str]

EmptyProofState = ProofState(steps=[])