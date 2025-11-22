from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class TheoremState:
    label: str
    floating_args: List[str]
    essential_args: List[str]
    essential_theorems: List[str]
    assertion: str

EmptyTheoremState = TheoremState(label='', floating_args=[], essential_args=[], essential_theorems=[], assertion='')
