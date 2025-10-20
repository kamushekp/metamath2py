
from typing import TypedDict
from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution


class A7OI2_FloatingArgs(TypedDict):
    ph: str
    x: str
    A: str
    B: str



class A7OI2_EssentialArgs(TypedDict):
    pass



class A7OI2:
    """"""
    def __init__(self):
        self.assertion = r"""|- ( A = B -> ( E! x e. A ph <-> E! x e. B ph ) )"""
        
    def call(self, floatings: A7OI2_FloatingArgs, essentials: A7OI2_EssentialArgs):
        assertion_substituted = apply_substitution(self.assertion, floatings)
        return assertion_substituted

