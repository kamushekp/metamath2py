from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.generated_patch import GeneratedPatch


@dataclass
class TrajectoryStep:
    task: Task
    result: Optional[GeneratedPatch] = None
