from dataclasses import dataclass
from typing import List

from mmverify.models.marked_stack import MarkedStackSample
from mmverify.models.mm_models import Statement, Symbol, Var


@dataclass
class Substitution:
    variable: Var
    substituted: List[Symbol]
    stack_mark: str


@dataclass
class SubstitutionResult:
    statement: Statement
    substituted: List[Substitution]


def apply_subst(statement: Statement, substitution: dict[Var, MarkedStackSample]) -> SubstitutionResult:
    """Return the token list resulting from the given substitution
    (dictionary) applied to the given statement (token list).
    """
    result = []
    substituted = []
    for tok in statement.statement_content:
        variable = Var(tok.content)
        if variable in substitution:
            s = Substitution(variable=variable,
                             substituted=substitution[variable].statement.statement_content,
                             stack_mark=substitution[variable].mark)
            substituted.append(s)
            result.extend(substitution[variable].statement.statement_content)
        else:
            result.append(variable)
    return SubstitutionResult(statement=Statement(statement_content=result), substituted=substituted)
