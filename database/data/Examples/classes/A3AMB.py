
from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution


class A3AMB_FloatingArgs(TypedDict):
    ph: str
    ps: str
    ch: str
    th: str
    ta: str



class A3AMB_EssentialArgs(TypedDict):
    essential_1: str
    essential_2: str



class A3AMB:
    """"""
    def __init__(self):
        self.essential_1 = r"""|- ( ( if- ( ch , ph , ps ) <-> ph ) -> ( ta <-> th ) )"""
        self.essential_2 = r"""|- ta"""

        self.assertion = r"""|- ( ch -> th )"""
        
    def call(self, floatings: A3AMB_FloatingArgs, essentials: A3AMB_EssentialArgs):
        essential_1_substituted = apply_substitution(self.essential_1, floatings)
        if "essential_1" not in essentials:
            raise Exception("essential_1 must be in essentials")
        if essentials["essential_1"] != essential_1_substituted:
            raise Exception(f'essentials["essential_1"] must be equal {essential_1_substituted} but was {essentials["essential_1"]}')
        essential_2_substituted = apply_substitution(self.essential_2, floatings)
        if "essential_2" not in essentials:
            raise Exception("essential_2 must be in essentials")
        if essentials["essential_2"] != essential_2_substituted:
            raise Exception(f'essentials["essential_2"] must be equal {essential_2_substituted} but was {essentials["essential_2"]}')
        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted

