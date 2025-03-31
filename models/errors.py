class MMError(Exception):
    """Class of Metamath errors."""
    pass


class StackUnderflowError(Exception):
    def __init__(self, full_statement, hypothesis_amount):
        message = f"Stack underflow: proof step {full_statement} requires too many ({hypothesis_amount}) hypotheses."
        super().__init__(message)


class StackFloatingError(Exception):
    def __init__(self, entry, typecode, var):
        message = f"Proof stack entry {entry} does not match floating  hypothesis ({typecode}, {var})."
        super().__init__(message)


class StackEssentialError(Exception):
    def __init__(self, entry, substituted_hypotheses):
        message = f"Proof stack entry {entry} does not match essential hypothesis {substituted_hypotheses}."
        super().__init__(message)


class DisjointVariableError(Exception):
    def __init__(self, x0, y0):
        message = f"Disjoint variable violation:  {x0} , {y0}"
        super().__init__(message)


class EmptyStackError(Exception):
    def __init__(self):
        message = "Empty stack at end of proof."
        super().__init__(message)


class OverfullStackError(Exception):
    def __init__(self):
        message = "Stack has more than one entry at end of proof"
        super().__init__(message)


class NonMatchingStackError(Exception):
    def __init__(self, stack_entry, conclusion):
        message = f"Stack entry {stack_entry} does not match proved assertion {conclusion}."
        super().__init__(message)


class LabelNotFoundError(Exception):
    def __init__(self, label):
        message = f"No statement information found for label {label}"
        super().__init__(message)


class LabelNotActiveError(Exception):
    def __init__(self, label):
        message = f"The label {label} is the label of a nonactive hypothesis."
        super().__init__(message)


class LabelMultipleDefinedError(Exception):
    def __init__(self, label):
        message = f"Label {label} multiply defined."
        super().__init__(message)


class CompressedProofsError(Exception):
    def __init__(self):
        message = 'Compressed proofs are not supported'
        super().__init__(message)


class UnknownTokenError(Exception):
    def __init__(self, tok):
        message = f"Unknown token: '{tok}'."
        super().__init__(message)


class UnexpectedClosingBracketError(Exception):
    def __init__(self):
        message = "Unexpected '$)' while not within a comment"
        super().__init__(message)


class LabelNotDefinedError(Exception):
    def __init__(self, _type):
        message = f'{_type} must have label'
        super().__init__(message)


class StatementLengthIncorrectError(Exception):
    def __init__(self, statement):
        message = f'$f must have length 2 but is {statement}'
        super().__init__(message)
