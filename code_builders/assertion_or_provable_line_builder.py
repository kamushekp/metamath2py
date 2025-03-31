from typing import List

from mmverify.code_builders.pythonic_names_handler import PythonicNamesHandler
from mmverify.models.marked_stack import MarkedStackSample
from mmverify.models.mm_models import Statement, FloatingHyp, Var


class AssertionOrProvableLineBuilder:
    def __init__(self):
        self.pythonic_name_handler = PythonicNamesHandler()

        self._added_mark = None
        self._comment = None
        self._floating_args = None
        self._name = None

        self._essential_args = []
        self._essential_index = 1

    def add_statement_name(self, name: str):
        self._name = self.pythonic_name_handler.map_name(name)
        return self._name

    def add_floating_substitution(self, floatings: List[FloatingHyp], subst: dict[Var, MarkedStackSample]):
        args: List[str] = []
        for floating in floatings:
            arg = f'"{floating.variable.content}": {subst[floating.variable].mark}'
            args.append(arg)
        self._floating_args = '{' + ', '.join(args) + '}'

    def add_essential_substitution(self, stack_mark: str):
        arg = f'"essential_{self._essential_index}": {stack_mark}'
        self._essential_args.append(arg)
        self._essential_index += 1

    def add_comment(self, used_stack_samples: List[MarkedStackSample], conclusion: Statement):
        self._comment = f"{marked_stack_samples_as_comment(used_stack_samples)}. Hence, {conclusion}"

    def add_stack_added_mark(self, added_mark: str):
        self._added_mark = added_mark

    def build(self):
        args = f"{self._floating_args}"
        if len(self._essential_args) > 0:
            essential_args = '{' + ', '.join(self._essential_args) + '}'
            args += f", {essential_args}"
        else:
            args += ', {}'

        return f"{self._added_mark} = {self._name}().call({args})" # {self._comment}"


def marked_stack_samples_as_comment(samples: List[MarkedStackSample]):
    return ', '.join([f"{s.mark}={s.statement}" for s in samples])
