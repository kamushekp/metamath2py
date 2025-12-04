from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from saplings.dtos.theorem_state import TheoremState


@dataclass
class PatchTheoremStateOp:
    field: Literal["label", "floating_args", "essential_args", "required_theorem_premise_premises", "assertion"]
    operation: Literal["remove", "replace", "insert"]
    content: str
    index: Optional[int] = None

    def validate(self, target: TheoremState):
        is_list_field = self.field in {"floating_args", "essential_args", "required_theorem_premise_premises"}
        if self.operation == "insert" and not is_list_field:
            raise ValueError(f"Insert is only valid for list fields, got {self.field}")
        if not is_list_field and self.index is not None:
            raise ValueError(f"Index is not applicable for scalar field {self.field}")

        if not is_list_field:
            return

        seq: Sequence[str] = getattr(target, self.field)
        if self.operation == "remove" or self.operation == "replace":
            if self.index is None:
                raise ValueError(f"Index is required for {self.operation} on {self.field}")
            if self.index < 0 or self.index >= len(seq):
                raise IndexError(f"Index {self.index} out of bounds for {self.field} (size {len(seq)})")
        if self.operation == "insert" and self.index is not None:
            if self.index < 0 or self.index > len(seq):
                raise IndexError(f"Index {self.index} out of bounds for insert into {self.field} (size {len(seq)})")

    def apply(self, target: TheoremState):
        self.validate(target)
        is_list_field = self.field in {"floating_args", "essential_args", "required_theorem_premise_premises"}

        if is_list_field:
            seq = getattr(target, self.field)
            if self.operation == "insert":
                if self.index is None:
                    seq.append(self.content)
                else:
                    seq.insert(self.index, self.content)
            elif self.operation == "remove":
                seq.pop(self.index)
            elif self.operation == "replace":
                seq[self.index] = self.content
            return

        if self.operation == "remove":
            setattr(target, self.field, list())
        elif self.operation == "replace":
            setattr(target, self.field, self.content)
        else:
            raise ValueError(f"Unsupported operation {self.operation} for scalar field {self.field}")
