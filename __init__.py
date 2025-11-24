"""metamath2py package."""

from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent
_INNER_PKG = _PKG_ROOT / "metamath2py"
if _INNER_PKG.exists():
    __path__.insert(0, str(_INNER_PKG))

from .llm_authoring import (
    AuthoringWorkspace,
    ProofAuthor,
    ProofCheckResult,
    TheoremClassAuthor,
    ValidationIssue,
    WriteResult,
)

__all__ = [
    "AuthoringWorkspace",
    "ProofAuthor",
    "ProofCheckResult",
    "TheoremClassAuthor",
    "ValidationIssue",
    "WriteResult",
]
