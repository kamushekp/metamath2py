import re
from typing import List

from code_builders.postprocessor import replace_class_variables
from code_builders.pythonic_names_handler import PythonicNamesHandler
from models.errors import MMError
from models.mm_models import EssentialHyp, FloatingHyp, Statement, StatementType, Assertion

tabs_4 = '    '
tabs_8 = '        '

FLOATING_ARGS_PATTERN = """
class {NAME}_FloatingArgs(TypedDict):
{FLOATING_ARGS_DEFINITION}
"""

ESSENTIAL_ARGS_PATTERN = """
class {NAME}_EssentialArgs(TypedDict):
{ESSENTIAL_ARGS_DEFINITION}
"""

CLASS_PATTERN = '''
class {NAME}:
    """{COMMENT}"""
    def __init__(self):
{ESSENTIALS_DEFINITION}        self.assertion = r"""{ASSERTION}"""
        
    def call(self, floatings: {NAME}_FloatingArgs, essentials: {NAME}_EssentialArgs):
{ESSENTIAL_SUBSTITUTION}        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted
'''
GENERAL_PATTERN = """
from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution

{FLOATING_ARGS_PATTERN}

{ESSENTIAL_ARGS_PATTERN}

{CLASS_PATTERN}
"""

PATTERN_PROOF = ('''{IMPORTED_STATEMENTS}
class {NAME}_proof({NAME}):
    def proof(self):
{PROOF_LINES}
{LAST_STEP}
''')



pythonic_name_handler = PythonicNamesHandler()
class ClassBuilder:
    def __init__(self):
        self.pythonic_name_handler = pythonic_name_handler

        self._COMMENT = None
        self._NAME = None

        # import section
        self._IMPORTED_STATEMENTS = []

        # class section
        self._FLOATING_ARGS_DEFINITION = None
        self._ESSENTIAL_ARGS_DEFINITION = None

        # init section
        self._ESSENTIALS_DEFINITION = ''
        self._ASSERTION = None

        # proof section
        self._PROOF_LINES = ''
        self._LAST_STEP = None

        # call section
        self._ESSENTIAL_SUBSTITUTION = ''

        self._essential_map = {}
        self._floating_map = {}

        self.floatings_kinds = []

    @staticmethod
    def build_comment(comment):
        comment = comment.replace("\n", ' ')
        regex_contributed = r'\(Contributed by [^")]+\)'
        regex_proof_shortened = r'\(Proof shortened [^")]+\)'
        regex_proof_revised = r'\(Revised by [^")]+\)'

        comment = re.sub(regex_contributed, "", comment)
        comment = re.sub(regex_proof_shortened, "", comment)
        comment = re.sub(regex_proof_revised, "", comment)
        return comment

    def set_comment(self, comment):
        #comment = textwrap.fill(comment, 70, subsequent_indent='    ')
        self._COMMENT = ''  # do not use comment in built class
        self._UNINDENTED_COMMENT = ClassBuilder.build_comment(comment)#textwrap.fill(comment, 70)

    def set_statement_name(self, name: str):
        self._ORIGINAL_NAME = name
        self._NAME = self.pythonic_name_handler.map_name(name)

    @staticmethod
    def build_essentials(essentials_count: int):
        if essentials_count == 0:
            return f'{tabs_4}pass'

        essentials_class_args = []

        for i in range(1, essentials_count + 1):
            essentials_class_args.append(f'{tabs_4}essential_{i}: str')

        return '\n'.join(essentials_class_args)

    def set_essentials(self, essentials: List[EssentialHyp]):

        essentials_method_body = ''

        self._ESSENTIAL_ARGS_DEFINITION = ClassBuilder.build_essentials(len(essentials))

        for i, essential in enumerate(essentials, 1):
            self_var = f'self.essential_{i}'

            content = essential.statement_content
            content = [c.content for c in content]
            content = ' '.join(content)

            essentials_method_body += f'{tabs_8}{self_var} = r"""{content}"""\n'
            self._essential_map[content] = self_var

        if len(essentials_method_body) > 0:
            essentials_method_body += '\n'
        self._ESSENTIALS_DEFINITION = essentials_method_body

        self._ESSENTIAL_SUBSTITUTION = ClassBuilder.build_essential_substitution(len(essentials))

    @staticmethod
    def build_essential_substitution(essentials_amount):
        essentials_substitutions = []
        for i in range(1, essentials_amount + 1):
            first_exception_message = f'essential_{i} must be in essentials'
            second_exception_message = f'essentials["essential_{i}"] must be equal ' + '{' + f'essential_{i}_substituted' + '} but was ' '{' + f'essentials["essential_{i}"]' + '}'
            essential_substitution = (
                f'{tabs_8}essential_{i}_substituted = apply_substitution(self.essential_{i}, floatings)\n'
                f'{tabs_8}if "essential_{i}" not in essentials:\n'
                f'{tabs_8}{tabs_4}raise Exception("{first_exception_message}")\n'
                f'{tabs_8}if essentials["essential_{i}"] != essential_{i}_substituted:\n'
                f"{tabs_8}{tabs_4}raise Exception(f'{second_exception_message}')"
            )
            essentials_substitutions.append(essential_substitution)

        if len(essentials_substitutions) > 0:
            return '\n'.join(essentials_substitutions) + '\n'
        return ''

    @staticmethod
    def build_floatings(floatings: List[str]):
        if len(floatings) == 0:
            return f'{tabs_4}pass'

        floating_class_args = []
        for i, floating in enumerate(floatings, 1):
            floating_class_args.append(f'{tabs_4}{floating}: str')

        return '\n'.join(floating_class_args)

    def set_floatings(self, floatings: List[FloatingHyp]):
        if len(floatings) > 0:
            for floating in floatings:
                self.floatings_kinds.append(floating.variable.content)

        self._FLOATING_ARGS_DEFINITION = ClassBuilder.build_floatings([f.variable.content for f in floatings])

    def append_line_in_proof(self, line: str):
        self._PROOF_LINES += f"{tabs_8}{line}\n"

    def set_assertion(self, assertion: Assertion):
        statement = assertion.statement
        self._ASSERTION = ' '.join([c.content for c in statement.statement_content])
        self.set_essentials(assertion.essential)
        self.set_floatings(assertion.floating)

    @staticmethod
    def build_last_step(last_element_mark: str):
        exception_message = last_element_mark + ' was equal ' + '{' + f'{last_element_mark}' + '}, but expected it to be equal to assertion: {self.assertion}'
        return f'{tabs_8}if {last_element_mark} != self.assertion:\n' \
               f'{tabs_8}{tabs_4}raise Exception(f"{exception_message}")'

    def set_last_step(self, last_element_mark: str):
        self._LAST_STEP = ClassBuilder.build_last_step(last_element_mark)

    def add_essential_or_floating(self, statement_type: StatementType, stack_mark: str, statement: Statement):
        if statement_type == StatementType.floating:
            self.append_line_in_proof(f"{stack_mark} = {statement}")
        elif statement_type == StatementType.essential:
            content = [c.content for c in statement.statement_content]
            content = ' '.join(content)
            self.append_line_in_proof(f"{stack_mark} = {self._essential_map[content]}")
        else:
            raise MMError()

    def add_imported_statement(self, statement_name: str):
        self._IMPORTED_STATEMENTS.append(statement_name)

    @staticmethod
    def build_imports(statement_name: str, imported_statements: List[str]) -> str:
        default_import = f'''from metamath2py.classes.{statement_name} import {statement_name}\n'''
        imported_statements = [f'from metamath2py.classes.{name} import {name}' for name in set(imported_statements)]
        imported_statements = '\n'.join(imported_statements)
        imported_statements = default_import + imported_statements + '\n'
        return imported_statements

    def build(self):

        if self._PROOF_LINES == '':
            # when axiom
            self._PROOF_LINES = f'{tabs_8}pass'
            self._LAST_STEP = ''

        imported_statements = ClassBuilder.build_imports(self._NAME, self._IMPORTED_STATEMENTS)

        FLOATING_ARGS = FLOATING_ARGS_PATTERN.format(
            NAME=self._NAME,
            FLOATING_ARGS_DEFINITION=self._FLOATING_ARGS_DEFINITION
        )

        ESSENTIAL_ARGS = ESSENTIAL_ARGS_PATTERN.format(
            NAME=self._NAME,
            ESSENTIAL_ARGS_DEFINITION=self._ESSENTIAL_ARGS_DEFINITION,
        )
        CLASS = CLASS_PATTERN.format(
            NAME=self._NAME,
            ASSERTION=self._ASSERTION,
            ESSENTIALS_DEFINITION=self._ESSENTIALS_DEFINITION,
            COMMENT=self._COMMENT,
            ESSENTIAL_SUBSTITUTION = self._ESSENTIAL_SUBSTITUTION,

        )
        executable_class = GENERAL_PATTERN.format(
            ESSENTIAL_ARGS_PATTERN=ESSENTIAL_ARGS,
            FLOATING_ARGS_PATTERN=FLOATING_ARGS,
            CLASS_PATTERN=CLASS
        )

        executable_proof = PATTERN_PROOF.format(
            NAME=self._NAME,
            PROOF_LINES=self._PROOF_LINES,
            LAST_STEP=self._LAST_STEP,
            IMPORTED_STATEMENTS=imported_statements)

        executable_class = replace_class_variables(executable_class)
        executable_proof = replace_class_variables(executable_proof)

        return {
            "floatings": FLOATING_ARGS,
            "essentials": ESSENTIAL_ARGS,
            "class": CLASS,
            "executable_class": executable_class,
            "executable_proof": executable_proof,
            "proof_lines": self._PROOF_LINES,
            "original_name": self._ORIGINAL_NAME,
            "comment":self._UNINDENTED_COMMENT,
            "name":self._NAME,
        }
