from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from saplings.dtos.tasks.patches.patch_set import PatchSet
from saplings.dtos.tasks.create_node_task import CreateNodeTask


@dataclass
class TaskTransition:
    task_before: CreateNodeTask
    patch_set: PatchSet
    task_after: CreateNodeTask

    def to_candidate_key(self) -> str:
        """Generate a deterministic hash representing this transition content."""
        payload = {
            "before": self.task_before.to_dict(),
            "patch": self.patch_set.to_dict(),
            "after": self.task_after.to_dict(),
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
