from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Tuple

from saplings.dtos.tasks.generated_patch import GeneratedPatch
from saplings.dtos.tasks.task import Task


@dataclass
class TaskTransition:
    task: Task
    result: GeneratedPatch

    def to_candidate_key(self) -> str:
        pass
