from __future__ import annotations

from dataclasses import dataclass
from typing import List

from saplings.dtos.evaluations.node_score import NodeScore
from saplings.dtos.tasks.task_transition import TaskTransition


@dataclass
class SearchResult:
    trajectory: List[TaskTransition]
    node_score: NodeScore
    is_solution: bool
