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
        key = str(self.task_before) + str(self.patch_set) + str(self.task_after)
        serialized = json.dumps(key, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
