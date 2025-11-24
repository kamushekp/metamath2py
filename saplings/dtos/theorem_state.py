from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class RequiredTheorem:
    left: str
    right: str

@dataclass
class TheoremState:
    label: str
    floating_args: List[str]
    essential_args: List[str]
    required_theorems: List[RequiredTheorem]
    assertion: str

EmptyTheoremState = TheoremState(label='', floating_args=[], essential_args=[], required_theorems=[], assertion='')
