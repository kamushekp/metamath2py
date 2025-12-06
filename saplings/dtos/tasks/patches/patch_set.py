from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List

from saplings.dtos.tasks.patches.patch_proof_state_op import PatchProofStateOp
from saplings.dtos.tasks.patches.patch_theorem_state_op import PatchTheoremStateOp
from saplings.dtos.tasks.create_node_task import CreateNodeTask


@dataclass
class PatchSet:
    change_description: str = ""
    next_step_ideas: str = ""
    theorem_ops: List[PatchTheoremStateOp] = field(default_factory=list)
    proof_ops: List[PatchProofStateOp] = field(default_factory=list)

    def apply(self, task: CreateNodeTask) -> CreateNodeTask:
        updated = copy.deepcopy(task)
        updated.next_step_ideas = self.next_step_ideas

        for op in self.theorem_ops:
            op.apply(updated.theorem)
        for op in self.proof_ops:
            op.apply(updated.proof)

        return updated


@dataclass
class PatchSetList:
    patch_sets: List[PatchSet]
