"""Utilities for verifying generated metamath2py proofs.

The old :mod:`verify_metamath2py_files` script executed dynamically built Python
strings with :func:`exec`.  That approach had a couple of notable drawbacks:

* stack traces were swallowed – only ``str(exception)`` was printed, which made it
  difficult to pinpoint the failing line or even the stage (import vs. proof
  execution);
* repeated executions reused Python's module cache, so editing a proof file and
  re-running the verifier could silently keep using the stale version;
* the verifier always assumed a flat directory structure and did not surface the
  module path that failed, which complicates debugging when proofs live in
  subpackages.

This module provides structured verification helpers that address those
shortcomings.  Each verification step returns a :class:`ProofCheckResult`
instance with the failing stage, the formatted traceback, and a boolean flag
indicating success.  The functions are intentionally side-effect free so that
higher-level tools – including LLM-facing authoring helpers – can consume the
results and present detailed feedback to users.
"""
from __future__ import annotations

import importlib
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Iterable, List, Optional

DEFAULT_PROOFS_PACKAGE = "metamath2py.proofs"


@dataclass
class ProofCheckResult:
    """Structured result of a proof verification attempt."""

    statement_name: str
    success: bool
    stage: str
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    def as_dict(self) -> dict[str, Optional[str]]:
        """Return a JSON-serialisable representation of the result."""

        return {
            "statement_name": self.statement_name,
            "success": self.success,
            "stage": self.stage,
            "error_message": self.error_message,
            "traceback": self.traceback,
        }


def _format_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def verify_proof(statement_name: str, *, package: str = DEFAULT_PROOFS_PACKAGE) -> ProofCheckResult:
    """Import ``package.statement_name`` and execute its ``proof`` method.

    Parameters
    ----------
    statement_name:
        Name of the module relative to ``package`` – e.g. ``"A1WQA"`` or
        ``"chapter.A1WQA"`` when proofs are organised in subpackages.
    package:
        Base package that contains proof modules.  The default mirrors the
        existing project layout.
    """

    module_name = f"{package}.{statement_name}" if statement_name else package
    try:
        if module_name in sys.modules:
            module = importlib.reload(sys.modules[module_name])
        else:
            module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - we want to surface all failures
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="import",
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    factory_name = f"{statement_name.split('.')[-1]}_proof"
    try:
        factory = getattr(module, factory_name)
    except AttributeError as exc:
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="lookup",
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    try:
        proof_instance = factory()
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="construction",
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    try:
        proof_instance.proof()
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="execution",
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    return ProofCheckResult(statement_name=statement_name, success=True, stage="success")


def iter_statement_names(root_path: str, *, package: str = DEFAULT_PROOFS_PACKAGE) -> Iterable[str]:
    """Yield module names relative to ``package`` for every ``.py`` file."""

    if not os.path.isdir(root_path):
        return []

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, root_path)
            module = rel_path[:-3].replace(os.sep, ".")
            yield module


def verify_all_proofs(root_path: str, *, package: str = DEFAULT_PROOFS_PACKAGE) -> List[ProofCheckResult]:
    """Verify every proof contained in ``root_path``."""

    results: List[ProofCheckResult] = []
    for statement_name in iter_statement_names(root_path, package=package):
        results.append(verify_proof(statement_name, package=package))
    return results
