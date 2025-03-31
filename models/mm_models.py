from typing import Union, List
from dataclasses import dataclass
from strenum import StrEnum


@dataclass
class Label:
    name: str

    def __hash__(self):
        return self.name.__hash__()

    def __str__(self):
        return f'Label: {self.name}'


@dataclass
class Symbol:
    content: str  # while reading, it is not simple to determine if this is a variable or constant, so because of that here is str type

    def __hash__(self):
        return self.content.__hash__()

    def __str__(self):
        return self.content

    def __repr__(self):
        return self.__str__()

@dataclass
class Var(Symbol):

    def as_constant(self):
        return Const(self.content)

    def __lt__(self, other):
        return self.content < other.content

    def __le__(self, other):
        return self.content <= other.content

    def __eq__(self, other):
        return self.content == other.content

    def __ne__(self, other):
        return self.content != other.content

    def __gt__(self, other):
        return self.content > other.content

    def __ge__(self, other):
        return self.content >= other.content

    def __hash__(self):
        return self.content.__hash__()

    def __str__(self):
        return self.content

    def __repr__(self):
        return self.__str__()


@dataclass
class Const(Symbol):
    def as_variable(self) -> Var:
        return Var(self.content)

    def __hash__(self):
        return self.content.__hash__()

    def __str__(self):
        return self.content

    def __repr__(self):
        return self.__str__()


class StatementType(StrEnum):
    constant = "$c"
    variable = "$v"
    floating = "$f"
    essential = "$e"
    assertion = "$a"
    provable = "$p"
    definition = "$d"
    end_token = "$="

    @staticmethod
    def try_cast(token: str) -> Union['StatementType', None]:
        try:
            return StatementType(token)
        except ValueError:
            return None


@dataclass
class Statement:
    statement_content: list[Symbol]

    def __hash__(self):
        return tuple(self.statement_content).__hash__()

    def __str__(self):
        content = " ".join([str(s) for s in self.statement_content])
        return f'"{content}"'

    def __repr__(self):
        return self.__str__()


@dataclass
class EssentialHyp(Statement):

    def __str__(self):
        return f'EssentialHyp: {" ".join([str(s) for s in self.statement_content])}'

    def __repr__(self):
        return self.__str__()


@dataclass
class FloatingHyp:
    const: Const
    variable: Var

    def __str__(self):
        return f'FloatingHyp: Const "{str(self.const)}" and Variable "{str(self.variable)}"'

    def __repr__(self):
        return self.__str__()


@dataclass
class Definition:
    x: Var
    y: Var

    def __hash__(self):
        return tuple([self.x.content, self.y.content]).__hash__()

    def __str__(self):
        return f'Definition: X is "{str(self.x)}" and Y is "{str(self.y)}"'

    def __repr__(self):
        return self.__str__()



@dataclass
class Assertion:
    definitions: set[Definition]
    floating: List[FloatingHyp]
    essential: List[EssentialHyp]
    statement: Statement


@dataclass
class FullStatement:
    label: Label
    statement_type: StatementType
    statement: Union[Statement, Assertion]

    def __str__(self):
        return f'FullStatement: Label is {self.label}, statement_type is "{str(self.statement_type)}" and statement is "{str(self.statement)}"'

    def __repr__(self):
        return self.__str__()
