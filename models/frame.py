import itertools
from typing import Iterable

from mmverify.models.mm_models import Var, FloatingHyp, Label, EssentialHyp, Definition, Statement
from mmverify.models.dict_with_colisions import DictWithCollisions


class Frame:
    def __init__(self) -> None:
        self._variables: set[Var] = set()
        self._definitions: set[Definition] = set()
        self._floatings: list[FloatingHyp] = []
        self._floating_labels: dict[Var, Label] = {}
        self._essentials: list[EssentialHyp] = []
        self._essential_labels: DictWithCollisions = DictWithCollisions(Statement, Label)
        # Note: both self._essentials and self._essential_labels are needed since the keys of
        # self._essential_labels form a set, but the order and repetitions of self._essentials
        # are needed.

        # Note: its is possible to have duplicates in self._essential_labels, for example: https://us.metamath.org/mpeuni/ablpnpcan.html and ablpnpcan.g is unused, used ablsubsub.g
        # It is by design: https://groups.google.com/g/metamath/c/ZEso3iMmJD4/m/k6Zo00iGAQAJ
        # so instead of self._essential_labels be dictionary, it needs to be dictionary with repetitions for collision (or use label as a additional key)

    def add_variable(self, variable: Var):
        self._variables.add(variable)

    def get_variables(self) -> Iterable[Var]:
        return self._variables

    def add_floating(self, floating: FloatingHyp, label: Label):
        self._floatings.append(floating)
        self._floating_labels[floating.variable] = label

    def get_floatings(self) -> Iterable[FloatingHyp]:
        return self._floatings

    def is_floating_variable_declared(self, variable: Var):
        return variable in self._floating_labels

    def add_definitions(self, statement: Statement):

        variable_list = [Var(e.content) for e in statement.statement_content]
        product = itertools.product(variable_list, variable_list)
        definitions = [Definition(x=min(x, y), y=max(x, y)) for x, y in product if x != y]
        self._definitions.update(definitions)

    def get_definitions(self) -> Iterable[Definition]:
        return self._definitions

    def get_floating_label(self, variable: Var) -> Label:
        return self._floating_labels[variable]

    def add_essential(self, statement: Statement, label: Label):
        essential = EssentialHyp(statement_content=statement.statement_content)
        self._essentials.append(essential)
        self._essential_labels.add(statement, label)

    def get_essentials(self) -> Iterable[EssentialHyp]:
        return self._essentials

    def get_floating_and_essential_labels(self) -> set[Label]:
        essential = list(self._essential_labels.iter_values())
        floating = list(self._floating_labels.values())
        return set(essential + floating)