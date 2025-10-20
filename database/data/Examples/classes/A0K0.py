
from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution


class A0K0_FloatingArgs(TypedDict):
    ph: str
    ps: str
    ch: str
    th: str
    ta: str



class A0K0_EssentialArgs(TypedDict):
    essential_1: str
    essential_2: str
    essential_3: str



class A0K0:
    """"""
    def __init__(self):
        self.essential_1 = r"""|- ph"""
        self.essential_2 = r"""|- ( ps -> ( ch -> th ) )"""
        self.essential_3 = r"""|- ( ph -> ( th -> ta ) )"""

        self.assertion = r"""|- ( ps -> ( ch -> ta ) )"""
        
    def call(self, floatings: A0K0_FloatingArgs, essentials: A0K0_EssentialArgs):
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
        essential_3_substituted = apply_substitution(self.essential_3, floatings)
        if "essential_3" not in essentials:
            raise Exception("essential_3 must be in essentials")
        if essentials["essential_3"] != essential_3_substituted:
            raise Exception(f'essentials["essential_3"] must be equal {essential_3_substituted} but was {essentials["essential_3"]}')
        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted

