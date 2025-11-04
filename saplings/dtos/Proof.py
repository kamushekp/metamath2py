from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SymbolDecl:
    """A declaration of a symbol used in theorem statements.

    For Metamath-style theorems, this may represent floating or essential
    hypotheses. We keep it flexible: `name` is the symbol, `sort` is the type
    (e.g., "wff", "setvar"), and `annotation` can carry extra info.
    """

    name: str
    sort: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TheoremState:
    """Structured fields sufficient to materialize a theorem module."""

    label: Optional[str] = None
    floating_args: List[SymbolDecl] = field(default_factory=list)
    essential_args: List[SymbolDecl] = field(default_factory=list)
    essential_theorems: List[str] = field(default_factory=list)
    assertion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "floating_args": [vars(x) for x in self.floating_args],
            "essential_args": [vars(x) for x in self.essential_args],
            "essential_theorems": list(self.essential_theorems),
            "assertion": self.assertion,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TheoremState":
        def _decls(items: List[Dict[str, Any]]) -> List[SymbolDecl]:
            return [SymbolDecl(**i) for i in items or []]

        return cls(
            label=data.get("label"),
            floating_args=_decls(data.get("floating_args", [])),
            essential_args=_decls(data.get("essential_args", [])),
            essential_theorems=list(data.get("essential_theorems", [])),
            assertion=data.get("assertion"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ProofStep:
    """Atomic step of a proof: reference and optional substitutions/notes."""

    reference: str
    substitutions: Dict[str, Any] = field(default_factory=dict)
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference": self.reference,
            "substitutions": dict(self.substitutions),
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofStep":
        return cls(
            reference=data.get("reference", ""),
            substitutions=dict(data.get("substitutions", {})),
            comment=data.get("comment"),
        )


@dataclass
class ProofState:
    """Structured representation of a proof as a sequence of steps."""

    steps: List[ProofStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofState":
        return cls(
            steps=[ProofStep.from_dict(s) for s in data.get("steps", [])],
            metadata=dict(data.get("metadata", {})),
        )

