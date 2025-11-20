from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from saplings.dtos.tasks.task_transition import TaskTransition


@dataclass
class Candidate:
    """Container describing a single branch returned by an Agents SDK run."""

    transition: TaskTransition
    context_items: Sequence[Any]

