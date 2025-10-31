"""Utilities for verifying generated metamath2py proofs.

The old :mod:`verify_metamath2py_files` script executed dynamically built Python
strings with :func:`exec`. That approach had a couple of notable drawbacks:

* stack traces were swallowed – only ``str(exception)`` was printed, which made it
  difficult to pinpoint the failing line or even the stage (import vs. proof
  execution);
* repeated executions reused Python's module cache, so editing a proof file and
  re-running the verifier could silently keep using the stale version;
* the verifier always assumed a flat directory structure and did not surface the
  module path that failed, which complicates debugging when proofs live in
  subpackages.

This module provides structured verification helpers that address those
shortcomings. Each verification step returns a :class:`ProofCheckResult`
instance with the failing stage, the formatted traceback, and a boolean flag
indicating success. The functions are intentionally side-effect free so that
higher-level tools – including LLM-facing authoring helpers – can consume the
results and present detailed feedback to users.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Iterable, List, Optional

from paths import PROJECT_PATH, PathsEnum, proofs_folder_path

_DEFAULT_PROJECT_ROOT = os.path.abspath(os.fspath(PROJECT_PATH))
_DEFAULT_PROOFS_ROOT = os.path.abspath(os.fspath(proofs_folder_path))
_DEFAULT_PROOFS_PACKAGE = (
    f"{PathsEnum.metamath2py_folder_name.value}.{PathsEnum.proofs_folder_name.value}"
)

if _DEFAULT_PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _DEFAULT_PROJECT_ROOT)


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


def _resolve_package_root(package: Optional[str]) -> Optional[str]:
    if package is None or package == _DEFAULT_PROOFS_PACKAGE:
        return _DEFAULT_PROOFS_ROOT

    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return None

    if spec is None or spec.submodule_search_locations is None:
        return None

    try:
        first_location = next(iter(spec.submodule_search_locations))
    except StopIteration:  # defensive, no search locations reported
        return None

    if first_location is None:
        return None

    return os.path.abspath(os.fspath(first_location))


def _verify_proof_at(
    statement_name: str,
    *,
    package: str,
    search_root: str,
) -> ProofCheckResult:
    """Import ``package.statement_name`` from ``search_root`` and execute its ``proof`` method."""

    module_name = f"{package}.{statement_name}"

    try:
        importlib.import_module(package)
    except ModuleNotFoundError as exc:
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="import",
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    trimmed_root = os.path.abspath(os.fspath(search_root))

    if module_name in sys.modules:
        sys.modules.pop(module_name, None)

    relative_parts = statement_name.split(".")
    module_filename = os.path.join(trimmed_root, *relative_parts) + ".py"

    if not os.path.isfile(module_filename):
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="import",
            error_message=f"Cannot find module file: {module_filename}",
            traceback=None,
        )

    spec = importlib.util.spec_from_file_location(module_name, module_filename)
    if spec is None or spec.loader is None:
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage="import",
            error_message=f"Unable to create module spec for {module_filename}",
            traceback=None,
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - we want to surface all failures
        sys.modules.pop(module_name, None)
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


def verify_proof(statement_name: str) -> ProofCheckResult:
    """Import the default ``metamath2py`` proof module and execute its ``proof`` method."""

    return _verify_proof_at(
        statement_name=statement_name,
        package=_DEFAULT_PROOFS_PACKAGE,
        search_root=_DEFAULT_PROOFS_ROOT,
    )


def iter_statement_names(root_path: Optional[str] = None) -> Iterable[str]:
    """Yield module names relative to ``package`` for every ``.py`` file.

    When ``root_path`` is not provided, the canonical proofs directory from
    :mod:`paths` is scanned, ensuring absolute paths are used regardless of the
    caller's working directory.
    """

    search_root = (
        os.path.abspath(os.fspath(root_path))
        if root_path is not None
        else _DEFAULT_PROOFS_ROOT
    )

    if not os.path.isdir(search_root):
        return []

    for dirpath, _, filenames in os.walk(search_root):
        for filename in filenames:
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, search_root)
            module = rel_path[:-3].replace(os.sep, ".")
            yield module


def verify_all_proofs() -> List[ProofCheckResult]:
    """Verify every proof contained in the default Metamath2py proofs package."""

    results: List[ProofCheckResult] = []
    for statement_name in iter_statement_names():
        results.append(
            _verify_proof_at(
                statement_name=statement_name,
                package=_DEFAULT_PROOFS_PACKAGE,
                search_root=_DEFAULT_PROOFS_ROOT,
            )
        )
    return results
