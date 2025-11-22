from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TheoremState:
    """Structured fields sufficient to materialize a theorem module."""

    label: Optional[str] = None
    floating_args: List[str] = field(default_factory=list)
    essential_args: List[str] = field(default_factory=list)
    essential_theorems: List[str] = field(default_factory=list)
    assertion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "floating_args": list(self.floating_args),
            "essential_args": list(self.essential_args),
            "essential_theorems": list(self.essential_theorems),
            "assertion": self.assertion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TheoremState":
        def _coerce_symbols(items) -> List[str]:
            coerced: List[str] = []
            for item in items or []:
                if isinstance(item, dict):
                    name = item.get("name")
                    if name is not None:
                        coerced.append(str(name))
                        continue
                    # Fallback: use keys to retain some value rather than dropping data
                    coerced.append(str(item))
                else:
                    coerced.append(str(item))
            return coerced

        return cls(
            label=data.get("label"),
            floating_args=_coerce_symbols(data.get("floating_args")),
            essential_args=_coerce_symbols(data.get("essential_args")),
            essential_theorems=[str(x) for x in data.get("essential_theorems", [])],
            assertion=data.get("assertion"),
        )


@dataclass
class ProofStep:
    """Atomic step of a proof: reference and optional substitutions/notes."""

    left: str
    right: str
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofStep":
        return cls(
            left=data.get("left", ""),
            right=data.get("right", ""),
            comment=data.get("comment"),
        )


@dataclass
class ProofState:
    """Structured representation of a proof as a sequence of steps."""

    steps: List[ProofStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofState":
        return cls(
            steps=[ProofStep.from_dict(s) for s in data.get("steps", [])],
        )
