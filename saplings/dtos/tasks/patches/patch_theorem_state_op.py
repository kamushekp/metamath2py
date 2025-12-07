from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, Union

from saplings.dtos.theorem_state import RequiredTheoremPremises, TheoremState


class TheoremOp(Protocol):
    def apply(self, target: TheoremState) -> None: ...


# Floating args
@dataclass
class AddFloating:
    value: str

    def apply(self, target: TheoremState) -> None:
        target.floating_args.append(self.value)


@dataclass
class RemoveFloating:
    name: str

    def apply(self, target: TheoremState) -> None:
        for idx, item in enumerate(target.floating_args):
            if item == self.name:
                target.floating_args.pop(idx)
                return
        raise ValueError(f"No floating arg '{self.name}' found to remove")


@dataclass
class ReplaceFloating:
    name: str
    new_value: str

    def apply(self, target: TheoremState) -> None:
        for idx, item in enumerate(target.floating_args):
            if item == self.name:
                target.floating_args[idx] = self.new_value
                return
        raise ValueError(f"No floating arg '{self.name}' found to replace")


# Essential args
@dataclass
class AddEssential:
    value: str

    def apply(self, target: TheoremState) -> None:
        target.essential_args.append(self.value)


@dataclass
class RemoveEssential:
    name: str

    def apply(self, target: TheoremState) -> None:
        for idx, item in enumerate(target.essential_args):
            if item == self.name:
                target.essential_args.pop(idx)
                return
        raise ValueError(f"No essential arg '{self.name}' found to remove")


@dataclass
class ReplaceEssential:
    name: str
    new_value: str

    def apply(self, target: TheoremState) -> None:
        for idx, item in enumerate(target.essential_args):
            if item == self.name:
                target.essential_args[idx] = self.new_value
                return
        raise ValueError(f"No essential arg '{self.name}' found to replace")


# Required premises
@dataclass
class AddPremise:
    left: str
    right: str

    def apply(self, target: TheoremState) -> None:
        target.required_theorem_premises.append(RequiredTheoremPremises(left=self.left, right=self.right))


@dataclass
class RemovePremise:
    left: str

    def apply(self, target: TheoremState) -> None:
        for idx, premise in enumerate(target.required_theorem_premises):
            if premise.left == self.left:
                target.required_theorem_premises.pop(idx)
                return
        raise ValueError(f"No premise '{self.left}' found to remove")


@dataclass
class ReplacePremise:
    left: str
    new_right: str

    def apply(self, target: TheoremState) -> None:
        for idx, premise in enumerate(target.required_theorem_premises):
            if premise.left == self.left:
                target.required_theorem_premises[idx] = RequiredTheoremPremises(left=self.left, right=self.new_right)
                return
        raise ValueError(f"No premise '{self.left}' found to replace")


# Scalars
@dataclass
class ReplaceLabel:
    new_label: str

    def apply(self, target: TheoremState) -> None:
        target.label = self.new_label


@dataclass
class ReplaceAssertion:
    new_assertion: str

    def apply(self, target: TheoremState) -> None:
        target.assertion = self.new_assertion


TheoremOpUnion = Union[
    AddFloating,
    RemoveFloating,
    ReplaceFloating,
    AddEssential,
    RemoveEssential,
    ReplaceEssential,
    AddPremise,
    RemovePremise,
    ReplacePremise,
    ReplaceLabel,
    ReplaceAssertion,
]


def op_type(op: TheoremOpUnion) -> str:
    return op.__class__.__name__


def serialize_theorem_op(op: TheoremOpUnion) -> dict[str, str]:
    """Convert a theorem op dataclass to dict for logging/UI."""
    data = asdict(op)
    data["type"] = op_type(op)
    return data
