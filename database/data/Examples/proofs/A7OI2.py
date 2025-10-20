from metamath2py.classes.A7OI2 import A7OI2
from metamath2py.classes.CQ78Y import CQ78Y
from metamath2py.classes.YRM78 import YRM78

class A7OI2_proof(A7OI2):
    def proof(self):
        x_1 = "wff ph"
        x_2 = "setvar x"
        x_3 = "class A"
        x_4 = "class B"
        x_5 = "setvar x"
        x_6 = "class A"
        x_7 = CQ78Y().call({"x": x_5, "A": x_6}, {})
        x_8 = "setvar x"
        x_9 = "class B"
        x_10 = CQ78Y().call({"x": x_8, "A": x_9}, {})
        x_11 = YRM78().call({"ph": x_1, "x": x_2, "A": x_3, "B": x_4}, {"essential_1": x_7, "essential_2": x_10})

        if x_11 != self.assertion:
            raise Exception(f"x_11 was equal {x_11}, but expected it to be equal to assertion: {self.assertion}")
