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

    def to_candidate_key(self) -> Tuple[Any, ...]:
        result = self.result
        if result.patch:
            patch_sig = tuple(
                (
                    op.op,
                    op.path,
                    json.dumps(op.value, sort_keys=True, ensure_ascii=False)
                    if op.value is not None
                    else None,
                )
                for op in result.patch.ops
            )
            return (
                "patch",
                result.summary,
                result.terminal,
                patch_sig,
            )

        task_signature = json.dumps(self.task.to_dict(), sort_keys=True, ensure_ascii=False)
        return (
            "task",
            result.summary,
            result.terminal,
            tuple(result.used_theorems),
            task_signature,
        )
