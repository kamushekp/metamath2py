from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from saplings.dtos.tasks.patches.patch_proof_state_op import PatchProofStateOp
from saplings.dtos.tasks.patches.patch_theorem_state_op import PatchTheoremStateOp
from saplings.dtos.tasks.task import Task


@dataclass
class PatchSet:
    summary: str
    theorem_ops: List[PatchTheoremStateOp] = field(default_factory=list)
    proof_ops: List[PatchProofStateOp] = field(default_factory=list)

    def apply(self, task: Task) -> Task:
        updated = copy.deepcopy(task)

        for op in self.theorem_ops:
            op.apply(updated.theorem)
        for op in self.proof_ops:
            op.apply(updated.proof)

        return updated


@dataclass
class PatchSetList:
    patch_sets: List[PatchSet]