import itertools
from typing import Optional

from models.frame import Frame
from models.mm_models import Var, Label, Definition, Statement, Assertion


class FrameStack(list[Frame]):
    """Class of frame stacks, which extends lists (considered and used as
    stacks).
    """

    def push(self, frame: Frame) -> None:
        """Push an empty frame to the stack."""
        self.append(frame)


    def lookup_variable(self, variable: Var) -> bool:
        """Return whether the given token is an active variable."""
        for frame in self:
            if variable in set(frame.get_variables()):
                return True

        return False

    def lookup_definition(self, x: Var, y: Var) -> bool:
        """Return whether the given ordered pair of tokens belongs to an
        active disjoint variable statement.
        """
        definition = Definition(x=min(x, y), y=(max(x, y)))
        for frame in self:
            if definition in set(frame.get_definitions()):
                return True

        return False

    def lookup_floating(self, var: Var) -> Optional[Label]:
        """Return the label of the active floating hypothesis which types the
        given variable.
        """
        for frame in self:
            try:
                return frame.get_floating_label(var)
            except KeyError:
                pass
        return None  # Variable is not actively typed


    def find_variables(self, statement: Statement) -> set[Var]:
        """Return the set of variables in the given statement."""
        return {Var(symbol.content) for symbol in statement.statement_content if self.lookup_variable(Var(symbol.content))}

    def make_assertion(self, statement: Statement) -> Assertion:
        """Return a quadruple (disjoint variable conditions, floating
        hypotheses, essential hypotheses, conclusion) describing the given
        assertion.
        """
        essential_hypothesis = []
        for frame in self:
            for essential in frame.get_essentials():
                essential_hypothesis.append(essential)

        mand_vars = set()
        for hypotheses in itertools.chain(essential_hypothesis, [statement]):
            for tok in hypotheses.statement_content:
                variable = Var(tok.content)
                if self.lookup_variable(variable):
                    mand_vars.add(variable)

        definitions = set()
        for frame in self:
            for definition in frame.get_definitions():
                if definition.x in mand_vars and definition.y in mand_vars:
                    definitions.add(definition)

        floating_hypothesis = []
        for frame in self:
            for floating in frame.get_floatings():
                if floating.variable in mand_vars:
                    floating_hypothesis.append(floating)
                    mand_vars.remove(floating.variable)
        assertion = definitions, floating_hypothesis, essential_hypothesis, statement
        return Assertion(definitions=definitions,
                         floating=floating_hypothesis,
                         essential=essential_hypothesis,
                         statement=statement)
