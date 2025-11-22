from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TheoremState:
    label: str
    floating_args: List[str]
    essential_args: List[str]
    essential_theorems: List[str]
    assertion: str

EmptyTheoremState = TheoremState(label='', floating_args=[], essential_args=[], essential_theorems=[], assertion='')

@dataclass
class ProofStep:
    left: str
    right: str
    comment: Optional[str]


@dataclass
class ProofState:
    steps: List[ProofStep]

EmptyProofState = ProofState(steps=[])