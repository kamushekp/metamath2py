from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Tuple

from saplings.dtos.tasks.generated_patch import GeneratedPatch
from saplings.dtos.tasks.task import Task


@dataclass
class TaskTransition:
    task_before: Task
    patch: GeneratedPatch
    task_after: Task

    def to_candidate_key(self) -> str:
        """Generate a deterministic hash representing this transition content."""
        payload = {
            "before": self.task_before.to_dict(),
            "patch": self.patch.to_dict(),
            "after": self.task_after.to_dict(),
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
