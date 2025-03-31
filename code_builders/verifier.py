import itertools

from mmverify.code_builders.assertion_or_provable_line_builder import AssertionOrProvableLineBuilder
from mmverify.code_builders.class_builder import ClassBuilder
from mmverify.models.frame_stack import FrameStack
from mmverify.models.marked_stack import MarkedStackSample, MarkedStack
from mmverify.models.mm_models import StatementType, Statement, Var, Label, FullStatement
from mmverify.code_builders.substitution import apply_subst
from mmverify.models.errors import (DisjointVariableError,
                                    StackEssentialError,
                                    StackFloatingError,
                                    StackUnderflowError,
                                    LabelNotActiveError,
                                    LabelNotFoundError,
                                    CompressedProofsError,
                                    EmptyStackError,
                                    OverfullStackError,
                                    NonMatchingStackError)


def assert_proof(conclusion, stack: MarkedStack):
    if not stack:
        raise EmptyStackError()
    if len(stack) > 1:
        raise OverfullStackError()
    if stack.get_i_element(0).statement != conclusion:
        raise NonMatchingStackError(stack.get_i_element(0), conclusion)


def verify(frame_stack: FrameStack,
           labels: dict[Label, FullStatement],
           target_statement: Statement,
           proof: Statement,
           builder: ClassBuilder) -> None:
    if proof.statement_content[0].content == '(':  # compressed format
        raise CompressedProofsError()

    stack = MarkedStack()
    active_hypotheses = set()
    for frame in frame_stack:
        for label in frame.get_floating_and_essential_labels():
            active_hypotheses.add(label)

    for label in proof.statement_content:
        possible_label = Label(label.content)
        full_statement = labels.get(possible_label)
        if not full_statement:
            raise LabelNotFoundError(label)

        if full_statement.statement_type in {StatementType.essential, StatementType.floating}:
            if possible_label not in active_hypotheses:
                raise LabelNotActiveError(label)

        statement_type = full_statement.statement_type

        if statement_type in {StatementType.essential, StatementType.floating}:
            stack.append(full_statement.statement)
            builder.add_essential_or_floating(statement_type, stack.get_last_element_mark(), full_statement.statement)

        elif statement_type in {StatementType.assertion, StatementType.provable}:

            assertion_or_provable_line_builder = AssertionOrProvableLineBuilder()

            assertion = full_statement.statement
            definitions = assertion.definitions
            floatings = assertion.floating
            essentials = assertion.essential
            conclusion = assertion.statement
            hypothesis_amount = len(floatings) + len(essentials)
            stack_index = len(stack) - hypothesis_amount

            if stack_index < 0:
                raise StackUnderflowError(full_statement, hypothesis_amount)
            subst: dict[Var, MarkedStackSample] = {}
            for floating in floatings:
                typecode = floating.const
                var = floating.variable
                entry = stack.get_i_element(stack_index)
                if entry.statement.statement_content[0].content != typecode.content:
                    raise StackFloatingError(entry, typecode, var)
                subst[var] = MarkedStackSample(mark=entry.mark,
                                               statement=Statement(entry.statement.statement_content[1:]))
                stack_index += 1

            for essential in essentials:
                entry = stack.get_i_element(stack_index)
                substituted_hypotheses = apply_subst(essential, subst)
                if entry.statement != substituted_hypotheses.statement:
                    raise StackEssentialError(entry, substituted_hypotheses)

                assertion_or_provable_line_builder.add_essential_substitution(entry.mark)

                stack_index += 1

            for definition in definitions:
                x, y = definition.x, definition.y
                x_vars = frame_stack.find_variables(subst[x].statement)
                y_vars = frame_stack.find_variables(subst[y].statement)
                for x0, y0 in itertools.product(x_vars, y_vars):
                    if x0 == y0 or not frame_stack.lookup_definition(x0, y0):
                        raise DisjointVariableError(x0, y0)
            marked_stack_samples = stack.remove(hypothesis_amount)
            substituted_conclusion = apply_subst(conclusion, subst)
            assertion_or_provable_line_builder.add_floating_substitution(floatings, subst)

            stack.append(substituted_conclusion.statement)
            assertion_or_provable_line_builder.add_stack_added_mark(stack.get_last_element_mark())

            call_name = assertion_or_provable_line_builder.add_statement_name(full_statement.label.name)
            builder.add_imported_statement(call_name)

            assertion_or_provable_line_builder.add_comment(marked_stack_samples, substituted_conclusion.statement)
            builder.append_line_in_proof(assertion_or_provable_line_builder.build())

    builder.set_last_step(stack.get_last_element_mark())
    assert_proof(target_statement, stack)
