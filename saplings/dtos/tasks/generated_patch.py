from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from saplings.dtos.tasks.patches.patch_set import PatchSet


class GeneratedPatch(BaseModel):

    summary: str
    patch: Optional[PatchSet] = None
    used_theorems: List[str] = Field(default_factory=list)
    terminal: bool = False