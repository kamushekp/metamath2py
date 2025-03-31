from metamath2py.classes.A0K0 import A0K0
from metamath2py.classes.VLEL import VLEL
from metamath2py.classes.SW6P import SW6P

class A0K0_proof(A0K0):
    def proof(self):
        x_1 = "wff ps"
        x_2 = "wff ph"
        x_3 = "wff ch"
        x_4 = "wff th"
        x_5 = "wff ta"
        x_6 = "wff ph"
        x_7 = "wff ps"
        x_8 = self.essential_1
        x_9 = VLEL().call({"ph": x_6, "ps": x_7}, {"essential_1": x_8})
        x_10 = self.essential_2
        x_11 = self.essential_3
        x_12 = SW6P().call({"ph": x_1, "ps": x_2, "ch": x_3, "th": x_4, "ta": x_5}, {"essential_1": x_9, "essential_2": x_10, "essential_3": x_11})

        if x_12 != self.assertion:
            raise Exception(f"x_12 was equal {x_12}, but expected it to be equal to assertion: {self.assertion}")
