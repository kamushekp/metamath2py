from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, Union

from saplings.dtos.proof_state import ProofState, ProofStep


class ProofOp(Protocol):
    def apply(self, target: ProofState) -> None: ...


@dataclass
class AddStep:
    left: str
    right: str
    comment: str

    def apply(self, target: ProofState) -> None:
        target.steps.append(ProofStep(left=self.left, right=self.right, comment=self.comment))


@dataclass
class RemoveStep:
    left: str

    def apply(self, target: ProofState) -> None:
        for idx, step in enumerate(target.steps):
            if step.left == self.left:
                target.steps.pop(idx)
                return
        raise ValueError(f"No proof step with left='{self.left}' found to remove")


@dataclass
class ReplaceStep:
    left: str
    new_right: str
    new_comment: str

    def apply(self, target: ProofState) -> None:
        for idx, step in enumerate(target.steps):
            if step.left == self.left:
                target.steps[idx] = ProofStep(left=self.left, right=self.new_right, comment=self.new_comment)
                return
        raise ValueError(f"No proof step with left='{self.left}' found to replace")


ProofOpUnion = Union[AddStep, RemoveStep, ReplaceStep]


def proof_op_type(op: ProofOpUnion) -> str:
    return op.__class__.__name__


def serialize_proof_op(op: ProofOpUnion) -> dict[str, str]:
    data = asdict(op)
    data["type"] = proof_op_type(op)
    return data
