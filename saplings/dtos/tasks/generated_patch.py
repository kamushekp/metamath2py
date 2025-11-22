from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from saplings.dtos.tasks.patch import PatchSet


class GeneratedPatch(BaseModel):
    """Single container for agent outputs (previously TaskResult/TaskResultPayload)."""

    summary: str
    patch: Optional[PatchSet] = None
    used_theorems: List[str] = Field(default_factory=list)
    terminal: bool = False

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="before")
    @classmethod
    def _coerce_patch(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(values, dict):
            return values

        raw_patch = values.get("patch")
        if raw_patch is None or isinstance(raw_patch, PatchSet):
            return values

        # Expect a list of JSON patch operations
        values["patch"] = PatchSet.from_list(raw_patch)  # type: ignore[arg-type]
        return values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "patch": [vars(op) for op in self.patch.ops] if self.patch else None,
            "used_theorems": list(self.used_theorems),
            "terminal": bool(self.terminal),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GeneratedPatch":
        return cls(**payload)
