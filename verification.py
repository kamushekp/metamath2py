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
from types import ModuleType
from typing import Iterable, List, Optional

from strenum import StrEnum

try:
    from .paths import PROJECT_PATH, PathsEnum, proofs_folder_path, classes_folder_path
except ImportError:
    # Fallback for execution outside package context
    from paths import PROJECT_PATH, PathsEnum, proofs_folder_path, classes_folder_path

_DEFAULT_PROJECT_ROOT = os.path.abspath(os.fspath(PROJECT_PATH))
_DEFAULT_PROOFS_ROOT = os.path.abspath(os.fspath(proofs_folder_path))
_DEFAULT_CLASSES_ROOT = os.path.abspath(os.fspath(classes_folder_path))
_DEFAULT_PROOFS_PACKAGE = (
    f"{PathsEnum.metamath2py_folder_name.value}.{PathsEnum.proofs_folder_name.value}"
)
_DEFAULT_CLASSES_PACKAGE = (
    f"{PathsEnum.metamath2py_folder_name.value}.{PathsEnum.classes_folder_name.value}"
)

if _DEFAULT_PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _DEFAULT_PROJECT_ROOT)


class ProofCheckStage(StrEnum):
    IMPORT = "import"
    LOOKUP = "lookup"
    CONSTRUCTION = "construction"
    EXECUTION = "execution"
    SUCCESS = "success"


@dataclass
class ProofCheckResult:
    """Structured result of a proof verification attempt."""

    statement_name: str
    success: bool
    stage: ProofCheckStage
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    def as_dict(self) -> dict[str, Optional[str]]:
        """Return a JSON-serialisable representation of the result."""

        return {
            "statement_name": self.statement_name,
            "success": self.success,
            "stage": self.stage.value,
            "error_message": self.error_message,
            "traceback": self.traceback,
        }


def _format_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _ensure_namespace(package: str, path: str) -> None:
    """Ensure a package namespace exists in ``sys.modules`` with the given search path."""

    if not package:
        return

    normalized_path = os.path.abspath(os.fspath(path))
    module = sys.modules.get(package)

    if module is None:
        module = ModuleType(package)
        module.__path__ = [normalized_path]  # type: ignore[attr-defined]
        sys.modules[package] = module
    else:
        pkg_paths = list(getattr(module, "__path__", []))
        if normalized_path not in pkg_paths:
            pkg_paths.append(normalized_path)
            module.__path__ = pkg_paths  # type: ignore[attr-defined]

    parent_name, _, child_name = package.rpartition(".")
    if parent_name:
        parent_path = os.path.dirname(normalized_path)
        _ensure_namespace(parent_name, parent_path)
        parent_module = sys.modules[parent_name]
        if not hasattr(parent_module, child_name):
            setattr(parent_module, child_name, module)


def _load_module_from_path(module_name: str, file_path: str) -> ModuleType:
    """Load ``module_name`` from ``file_path`` and register it in ``sys.modules``."""

    normalized_path = os.path.abspath(os.fspath(file_path))

    if module_name in sys.modules:
        sys.modules.pop(module_name, None)

    if not os.path.isfile(normalized_path):
        raise ModuleNotFoundError(f"Cannot find module file: {normalized_path}")

    spec = importlib.util.spec_from_file_location(module_name, normalized_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create module spec for {normalized_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def _verify_proof_at(
    statement_name: str,
    *,
    package: str,
    search_root: str,
) -> ProofCheckResult:
    """Import ``package.statement_name`` from ``search_root`` and execute its ``proof`` method."""

    trimmed_root = os.path.abspath(os.fspath(search_root))
    module_name = f"{package}.{statement_name}"

    try:
        _ensure_namespace(package, trimmed_root)
        _ensure_namespace(_DEFAULT_CLASSES_PACKAGE, _DEFAULT_CLASSES_ROOT)
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage=ProofCheckStage.IMPORT,
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    class_module_name = f"{_DEFAULT_CLASSES_PACKAGE}.{statement_name}"
    class_path = os.path.join(_DEFAULT_CLASSES_ROOT, *statement_name.split(".")) + ".py"

    try:
        if os.path.isfile(class_path):
            _load_module_from_path(class_module_name, class_path)
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage=ProofCheckStage.IMPORT,
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    proof_path = os.path.join(trimmed_root, *statement_name.split(".")) + ".py"

    try:
        module = _load_module_from_path(module_name, proof_path)
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage=ProofCheckStage.IMPORT,
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
            stage=ProofCheckStage.LOOKUP,
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    try:
        proof_instance = factory()
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage=ProofCheckStage.CONSTRUCTION,
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    try:
        proof_instance.proof()
    except Exception as exc:  # noqa: BLE001
        return ProofCheckResult(
            statement_name=statement_name,
            success=False,
            stage=ProofCheckStage.EXECUTION,
            error_message=str(exc),
            traceback=_format_traceback(exc),
        )

    return ProofCheckResult(statement_name=statement_name, success=True, stage=ProofCheckStage.SUCCESS)


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
