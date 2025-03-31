from typing import Optional, Dict, Iterable

from tqdm import tqdm

from mmverify.code_builders.class_builder import ClassBuilder
from mmverify.code_builders.verifier import verify
from mmverify.models.frame import Frame
from mmverify.models.frame_stack import FrameStack
from mmverify.models.mm_models import (StatementType,
                                       Statement,
                                       Symbol,
                                       Const,
                                       Var,
                                       Label,
                                       FullStatement,
                                       FloatingHyp)
from mmverify.models.toks import Toks
from mmverify.models.errors import MMError, UnknownTokenError, LabelMultipleDefinedError, \
    UnexpectedClosingBracketError, LabelNotDefinedError, StatementLengthIncorrectError



class MM:
    """Class of ("abstract syntax trees" describing) Metamath databases."""

    def __init__(self) -> None:
        """Construct an empty Metamath database."""
        self._constants: set[Const] = set()
        self.frame_stack = FrameStack()
        self.labels: dict[Label, FullStatement] = {}

        self.comments = []

    def append_comment_if_exists(self, comment: Optional[str]):
        if comment:
            self.comments.append(comment)

    def is_constant_declared(self, const: Const):
        return const in self._constants

    def add_constant(self, tok: Const) -> None:
        """Add a constant to the database."""
        if self.is_constant_declared(tok):
            raise MMError(f'Constant already declared: {tok}')
        if self.frame_stack.lookup_variable(tok.as_variable()):
            raise MMError(f'Trying to declare as a constant an active variable: {tok}')
        self._constants.add(tok)

    def add_constants(self, statement: Statement):
        for symbol in statement.statement_content:
            constant = Const(symbol.content)
            self.add_constant(constant)

    def _add_variable(self, frame: Frame, tok: Var) -> None:
        """Add a variable to the frame stack top (that is, the current frame)
        of the database.  Allow local variable declarations.
        """
        if self.frame_stack.lookup_variable(tok):
            raise MMError('var already declared and active: {}'.format(tok))
        if self.is_constant_declared(tok.as_constant()):
            raise MMError('var already declared as constant: {}'.format(tok))
        frame.add_variable(tok)

    def add_variables(self, frame: Frame, statement: Statement):
        for symbol in statement.statement_content:
            variable = Var(symbol.content)
            self._add_variable(frame, variable)

    def add_floating(self, frame: Frame, typecode: Const, var: Var, label: Label) -> None:
        """Add a floating hypothesis (ordered pair (variable, typecode)) to
        the frame stack top (that is, the current frame) of the database.
        """
        if not self.frame_stack.lookup_variable(var):
            raise MMError('var in $f not declared: {}'.format(var))
        if not self.is_constant_declared(typecode):
            raise MMError('typecode in $f not declared: {}'.format(typecode))
        if any(frame.is_floating_variable_declared(var) for frame in self.frame_stack):
            raise MMError("var in $f already typed by an active  $f-statement: {}".format(var))
        floating = FloatingHyp(typecode, var)
        frame.add_floating(floating, label)

    def readstmt_aux(self, statement_type: StatementType, toks: Toks, end_token: str) -> Statement:
        """Read tokens from the input (assumed to be at the beginning of a
        statement) and return the list of tokens until the end_token
        (typically "$=" or "$.").
        """
        statement_content = []
        comment, tok = toks.readc()
        self.append_comment_if_exists(comment)
        while tok and tok != end_token:
            variable = Var(tok)
            constant = Const(tok)
            condition = statement_type in {StatementType.definition,
                                           StatementType.essential,
                                           StatementType.assertion,
                                           StatementType.provable}

            if condition and not (self.is_constant_declared(constant) or self.frame_stack.lookup_variable(variable)):
                raise MMError(f"Token {tok} is not an active symbol")
            condition = statement_type in {StatementType.essential,
                                           StatementType.assertion,
                                           StatementType.provable}
            if condition and self.frame_stack.lookup_variable(variable) and not self.frame_stack.lookup_floating(
                    variable):
                raise MMError(f"Variable {tok} in {statement_type}-statement is not typed  by an active $f-statement).")

            symbol = Symbol(tok)
            statement_content.append(symbol)
            comment, tok = toks.readc()
            self.append_comment_if_exists(comment)
        if not tok:
            raise MMError(f"Unclosed {statement_type}-statement at end of file.")
        assert tok == end_token
        return Statement(statement_content)

    def read_non_p_stmt(self, statement_type: StatementType, toks: Toks) -> Statement:
        """Read tokens from the input (assumed to be at the beginning of a
        non-$p-statement) and return the list of tokens until the next
        end-statement token '$.'.
        """
        return self.readstmt_aux(statement_type, toks, end_token="$.")

    def read_p_stmt(self, toks: Toks) -> tuple[Statement, Statement]:
        """Read tokens from the input (assumed to be at the beginning of a
        p-statement) and return the couple of lists of tokens (stmt, proof)
        appearing in "$p stmt $= proof $.".
        """
        stmt = self.readstmt_aux(StatementType.provable, toks, end_token="$=")
        proof = self.readstmt_aux(StatementType.end_token, toks, end_token="$.")
        return stmt, proof

    def read(self, toks: Toks) -> Iterable[Dict[str, str]]:

        pbar = tqdm()
        current_frame = Frame()
        self.frame_stack.push(current_frame)
        label = None
        prev_label = None
        comment, tok = toks.readc()
        self.append_comment_if_exists(comment)
        while tok:
            statement_type = StatementType.try_cast(tok)

            if statement_type == StatementType.constant:
                statement = self.read_non_p_stmt(statement_type, toks)
                self.add_constants(statement)
            elif statement_type == StatementType.variable:
                statement = self.read_non_p_stmt(statement_type, toks)
                self.add_variables(current_frame, statement)

            elif statement_type == StatementType.floating:
                statement = self.read_non_p_stmt(statement_type, toks)
                if not label:
                    raise LabelNotDefinedError('$f')

                if len(statement.statement_content) != 2:
                    raise StatementLengthIncorrectError(statement)
                typecode = Const(statement.statement_content[0].content)
                variable = Var(statement.statement_content[1].content)
                self.add_floating(current_frame, typecode, variable, label)
                full_statement = FullStatement(label, StatementType.floating, statement)
                self.labels[label] = full_statement
                label = None

            elif statement_type == StatementType.essential:
                if not label:
                    raise LabelNotDefinedError('$e')
                statement = self.read_non_p_stmt(statement_type, toks)
                current_frame.add_essential(statement, label)
                self.labels[label] = FullStatement(label, StatementType.essential, statement)
                label = None

            elif statement_type == StatementType.assertion:
                if not label:
                    raise LabelNotDefinedError('$a')
                print(f'working with {label.name}')
                comment = self.comments[-1]
                self.comments = []
                assertion = self.frame_stack.make_assertion(self.read_non_p_stmt(statement_type, toks))
                builder = ClassBuilder()
                builder.set_comment(comment)
                builder.set_statement_name(label.name)
                builder.set_assertion(assertion)
                self.labels[label] = FullStatement(label, StatementType.assertion, assertion)
                label = None
                yield builder.build()
                pbar.update()


            elif statement_type == StatementType.provable:
                if not label:
                    raise LabelNotDefinedError('$p')
                print(f'working with {label.name}')
                comment = self.comments[-1]
                self.comments = []
                statement, proof = self.read_p_stmt(toks)
                assertion = self.frame_stack.make_assertion(statement)

                builder = ClassBuilder()
                builder.set_comment(comment)
                builder.set_statement_name(label.name)
                builder.set_assertion(assertion)
                verify(frame_stack=self.frame_stack, labels=self.labels, target_statement=assertion.statement, proof=proof, builder=builder)
                self.labels[label] = FullStatement(label, StatementType.provable, assertion)
                label = None

                yield builder.build()
                pbar.update()

            elif statement_type == StatementType.definition:
                statement = self.read_non_p_stmt(statement_type, toks)
                current_frame.add_definitions(statement)
            elif tok == '${':
                current_frame = Frame()
                self.frame_stack.push(current_frame)
                prev_label = label
                label = None
            elif tok == '$}':
                self.frame_stack.pop()
                current_frame = self.frame_stack[-1]
                label = prev_label
            elif tok == '$)':
                raise UnexpectedClosingBracketError()
            elif tok[0] != '$':
                label = Label(tok)
                if label in self.labels:
                    raise LabelMultipleDefinedError(tok)
            else:
                raise UnknownTokenError(tok)
            comment, tok = toks.readc()
            self.append_comment_if_exists(comment)
