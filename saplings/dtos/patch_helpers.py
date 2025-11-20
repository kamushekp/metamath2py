from __future__ import annotations

from typing import Any, Dict, Optional

from saplings.dtos.tasks.patch import PatchOp, PatchSet
from saplings.dtos.proof import ProofStep


def _add(path: str, value: Any) -> PatchOp:
    return PatchOp(op="add", path=path, value=value)


def _replace(path: str, value: Any) -> PatchOp:
    return PatchOp(op="replace", path=path, value=value)


def _index_path(base: str, index: Optional[int]) -> str:
    if index is None:
        return f"{base}/-"
    return f"{base}/{index}"


def add_proof_step_patch(step: ProofStep, *, index: Optional[int] = None) -> PatchSet:
    return PatchSet(ops=[_add(_index_path("/proof/steps", index), step.to_dict())])


def replace_assertion_patch(text: str) -> PatchSet:
    return PatchSet(ops=[_replace("/theorem/assertion", text)])


def add_floating_arg_patch(name: str, *, sort: Optional[str] = None, annotation: Optional[Dict[str, Any]] = None, index: Optional[int] = None) -> PatchSet:
    payload = {"name": name}
    if sort is not None:
        payload["sort"] = sort
    if annotation is not None:
        payload["annotation"] = dict(annotation)
    return PatchSet(ops=[_add(_index_path("/theorem/floating_args", index), payload)])


def add_essential_arg_patch(name: str, *, sort: Optional[str] = None, annotation: Optional[Dict[str, Any]] = None, index: Optional[int] = None) -> PatchSet:
    payload = {"name": name}
    if sort is not None:
        payload["sort"] = sort
    if annotation is not None:
        payload["annotation"] = dict(annotation)
    return PatchSet(ops=[_add(_index_path("/theorem/essential_args", index), payload)])


def add_essential_theorem_patch(label: str, *, index: Optional[int] = None) -> PatchSet:
    return PatchSet(ops=[_add(_index_path("/theorem/essential_theorems", index), label)])


def replace_goal_patch(goal: str) -> PatchSet:
    return PatchSet(ops=[_replace("/goal", goal)])

