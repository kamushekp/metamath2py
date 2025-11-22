from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from saplings.dtos.tasks.patch import PatchSet


@dataclass
class TaskResult:
    """Represents the outcome produced by the agent crew for a task."""

    summary: str
    patch: Optional[PatchSet] = None
    used_theorems: List[str] = field(default_factory=list)
    terminal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "patch": [vars(op) for op in self.patch.ops] if self.patch else None,
            "used_theorems": list(self.used_theorems),
            "terminal": bool(self.terminal),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TaskResult":
        patch_payload = payload.get("patch")
        patch = PatchSet.from_list(patch_payload) if patch_payload else None

        return cls(
            summary=payload.get("summary", ""),
            used_theorems=list(payload.get("used_theorems", [])),
            patch=patch,
            terminal=bool(payload.get("terminal", False)),
        )

