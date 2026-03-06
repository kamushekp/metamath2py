from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution

class unprovable_P_eq_NP_FloatingArgs(TypedDict):
    T: str


class unprovable_P_eq_NP_EssentialArgs(TypedDict):
    essential_1: str


class unprovable_P_eq_NP:
    """Goal: Prove that P equals NP is unprovable"""
    def __init__(self):
        self.essential_1 = r"""|- Sound(T)"""
        self.assertion = r"""|- ~Prov(T, P = NP)"""

    def call(self, floatings: unprovable_P_eq_NP_FloatingArgs, essentials: unprovable_P_eq_NP_EssentialArgs):
        essential_1_substituted = apply_substitution(self.essential_1, floatings)
        if "essential_1" not in essentials:
            raise Exception("essential_1 must be in essentials")
        if essentials["essential_1"] != essential_1_substituted:
            raise Exception(f'essentials["essential_1"] must be equal {essential_1_substituted} but was {essentials["essential_1"]}')
        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted

