from dataclasses import dataclass
from typing import List

from mmverify.models.mm_models import Statement


@dataclass
class MarkedStackSample:
    mark: str
    statement: Statement

class MarkedStack:
    def __init__(self):
        self._stack: List[MarkedStackSample] = []
        self._counter: int = 1
        self.removed = []

    def append(self, statement: Statement):
        sample = MarkedStackSample(f'x_{self._counter}', statement)
        self._stack.append(sample)
        self._counter += 1

    def get_last_element_mark(self):
        return self._stack[-1].mark

    def __len__(self):
        return len(self._stack)

    def remove(self, amount) -> List[MarkedStackSample]:
        removed = []
        for _ in range(amount):
            removed.append(self._stack.pop())

        removed = list(reversed(removed))
        return removed

    def get_i_element(self, i) -> MarkedStackSample:
        return self._stack[i]
