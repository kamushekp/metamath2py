from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from saplings.dtos.tasks import PatchSet


class GeneratedPatch(BaseModel):

    summary: str
    patch: Optional[PatchSet] = None
    used_theorems: List[str] = Field(default_factory=list)
