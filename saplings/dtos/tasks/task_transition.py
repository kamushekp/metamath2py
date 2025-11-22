from __future__ import annotations

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
        pass
