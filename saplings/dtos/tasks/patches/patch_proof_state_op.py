from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from saplings.dtos.proof import ProofState, ProofStep


@dataclass
class PatchProofStateOp:
    operation: Literal["remove", "insert"]
    left: Optional[str] = None
    right: Optional[str] = None
    comment: Optional[str] = None

    def validate(self, target: ProofState):
        if target is None:
            raise ValueError("Cannot apply proof patch without a target ProofState")
        if self.operation == "insert":
            if not self.left or not self.right:
                raise ValueError("Insert requires both left and right values")
        if self.operation == "remove":
            if not self.left and not self.right:
                raise ValueError("Remove requires left or right to match against")

    def apply(self, target: ProofState):
        self.validate(target)
        seq = target.steps
        if self.operation == "insert":
            seq.append(ProofStep(left=self.left or "", right=self.right or "", comment=self.comment))
            return

        # remove: drop first matching step
        for idx, step in enumerate(seq):
            matches_left = self.left is None or step.left == self.left
            matches_right = self.right is None or step.right == self.right
            if matches_left and matches_right:
                seq.pop(idx)
                return
        raise ValueError("No matching proof step found to remove")
