from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution

class T_1PLUS1_FloatingArgs(TypedDict):
    one_plus_one_eq_two: str
    ph: str


class T_1PLUS1_EssentialArgs(TypedDict):
    essential_1: str
    essential_2: str
    essential_3: str
    essential_4: str
    essential_5: str


class T_1PLUS1:
    """Goal: Prove that 1 + 1 = 2"""
    def __init__(self):
        self.essential_1 = r"""|- 1 = 1"""
        self.essential_2 = r"""|- 2 = 1 + 1"""
        self.essential_3 = r"""|- 2 = 1 + 1"""
        self.essential_4 = r"""|- 1 = 1"""
        self.essential_5 = r"""|- 2 = 1 + 1"""
        self.assertion = r"""|- 1 + 1 = 2"""

    def call(self, floatings: T_1PLUS1_FloatingArgs, essentials: T_1PLUS1_EssentialArgs):
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
        essential_4_substituted = apply_substitution(self.essential_4, floatings)
        if "essential_4" not in essentials:
            raise Exception("essential_4 must be in essentials")
        if essentials["essential_4"] != essential_4_substituted:
            raise Exception(f'essentials["essential_4"] must be equal {essential_4_substituted} but was {essentials["essential_4"]}')
        essential_5_substituted = apply_substitution(self.essential_5, floatings)
        if "essential_5" not in essentials:
            raise Exception("essential_5 must be in essentials")
        if essentials["essential_5"] != essential_5_substituted:
            raise Exception(f'essentials["essential_5"] must be equal {essential_5_substituted} but was {essentials["essential_5"]}')
        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted

