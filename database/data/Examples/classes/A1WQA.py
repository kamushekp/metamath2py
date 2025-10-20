
from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution


class A1WQA_FloatingArgs(TypedDict):
    A: str
    B: str
    R: str
    O: str
    X: str



class A1WQA_EssentialArgs(TypedDict):
    essential_1: str
    essential_2: str



class A1WQA:
    """"""
    def __init__(self):
        self.essential_1 = r"""|- R = ( `' O " ( _V \ 1o ) )"""
        self.essential_2 = r"""|- O Fn X"""

        self.assertion = r"""|- ( A R B <-> ( A O B ) =/= (/) )"""
        
    def call(self, floatings: A1WQA_FloatingArgs, essentials: A1WQA_EssentialArgs):
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

