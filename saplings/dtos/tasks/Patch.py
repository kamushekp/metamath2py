from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import copy


@dataclass
class PatchOp:
    op: str  # 'add' | 'remove' | 'replace'
    path: str
    value: Any = None


@dataclass
class PatchSet:
    ops: List[PatchOp] = field(default_factory=list)

    @classmethod
    def from_list(cls, items: List[Dict[str, Any]]) -> "PatchSet":
        return cls(ops=[PatchOp(**i) for i in items or []])


def _split_ptr(path: str) -> List[str]:
    if not path:
        return []
    if path.startswith("/"):
        path = path[1:]
    if not path:
        return []
    parts = path.split("/")
    # JSON Pointer unescape
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def _resolve(container: Any, parts: List[str]) -> tuple[Any, str]:
    """Resolve pointer to (parent, last_key)."""
    if not parts:
        raise ValueError("Path must not be empty")
    curr = container
    for idx, part in enumerate(parts[:-1]):
        key = int(part) if isinstance(curr, list) else part
        curr = curr[key]
    return curr, parts[-1]


def apply_patch(doc: Any, patch: PatchSet) -> Any:
    """Apply a minimal JSON-Patch-like set of ops (add/remove/replace)."""
    target = copy.deepcopy(doc)
    for op in patch.ops:
        parts = _split_ptr(op.path)
        parent, last = _resolve(target, parts)
        if isinstance(parent, list):
            if last == "-":
                index = len(parent)
            else:
                index = int(last)
            if op.op == "add":
                parent.insert(index, op.value)
            elif op.op == "remove":
                parent.pop(index)
            elif op.op == "replace":
                parent[index] = op.value
            else:
                raise ValueError(f"Unsupported op: {op.op}")
        else:
            # dict-like
            key = last
            if op.op in ("add", "replace"):
                parent[key] = op.value
            elif op.op == "remove":
                if key in parent:
                    del parent[key]
            else:
                raise ValueError(f"Unsupported op: {op.op}")
    return target

