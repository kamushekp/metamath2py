from metamath2py.classes.A3X5J import A3X5J
from metamath2py.classes.T3VV7 import T3VV7
from metamath2py.classes.F5FY7 import F5FY7
from metamath2py.classes.BEXAY import BEXAY
from metamath2py.classes.TND7D import TND7D
from metamath2py.classes.GOUVK import GOUVK
from metamath2py.classes.LSSMX import LSSMX
from metamath2py.classes.V7JQ import V7JQ
from metamath2py.classes.QXYT1 import QXYT1
from metamath2py.classes.DNIG4 import DNIG4
from metamath2py.classes.RKWJG import RKWJG

class A3X5J_proof(A3X5J):
    def proof(self):
        x_1 = "setvar x"
        x_2 = "class A"
        x_3 = "class B"
        x_4 = GOUVK().call({"A": x_2, "B": x_3}, {})
        x_5 = "setvar y"
        x_6 = T3VV7().call({"x": x_5}, {})
        x_7 = "class A"
        x_8 = BEXAY().call({"A": x_6, "B": x_7}, {})
        x_9 = "setvar y"
        x_10 = T3VV7().call({"x": x_9}, {})
        x_11 = "class B"
        x_12 = BEXAY().call({"A": x_10, "B": x_11}, {})
        x_13 = V7JQ().call({"ph": x_8, "ps": x_12}, {})
        x_14 = "setvar y"
        x_15 = DNIG4().call({"ph": x_13, "x": x_14}, {})
        x_16 = "setvar y"
        x_17 = "class A"
        x_18 = "class B"
        x_19 = QXYT1().call({"x": x_16, "A": x_17, "B": x_18}, {})
        x_20 = "setvar y"
        x_21 = T3VV7().call({"x": x_20}, {})
        x_22 = "class A"
        x_23 = BEXAY().call({"A": x_21, "B": x_22}, {})
        x_24 = "setvar y"
        x_25 = T3VV7().call({"x": x_24}, {})
        x_26 = "class B"
        x_27 = BEXAY().call({"A": x_25, "B": x_26}, {})
        x_28 = V7JQ().call({"ph": x_23, "ps": x_27}, {})
        x_29 = "setvar x"
        x_30 = "setvar y"
        x_31 = "setvar y"
        x_32 = T3VV7().call({"x": x_31}, {})
        x_33 = "class A"
        x_34 = BEXAY().call({"A": x_32, "B": x_33}, {})
        x_35 = "setvar y"
        x_36 = T3VV7().call({"x": x_35}, {})
        x_37 = "class B"
        x_38 = BEXAY().call({"A": x_36, "B": x_37}, {})
        x_39 = "setvar x"
        x_40 = "setvar x"
        x_41 = "setvar y"
        x_42 = T3VV7().call({"x": x_41}, {})
        x_43 = "class A"
        x_44 = self.essential_1
        x_45 = LSSMX().call({"x": x_40, "A": x_42, "B": x_43}, {"essential_1": x_44})
        x_46 = "setvar x"
        x_47 = "setvar y"
        x_48 = T3VV7().call({"x": x_47}, {})
        x_49 = "class B"
        x_50 = self.essential_2
        x_51 = LSSMX().call({"x": x_46, "A": x_48, "B": x_49}, {"essential_1": x_50})
        x_52 = TND7D().call({"ph": x_34, "ps": x_38, "x": x_39}, {"essential_1": x_45, "essential_2": x_51})
        x_53 = F5FY7().call({"ph": x_28, "x": x_29, "y": x_30}, {"essential_1": x_52})
        x_54 = RKWJG().call({"x": x_1, "A": x_4, "B": x_15}, {"essential_1": x_19, "essential_2": x_53})

        if x_54 != self.assertion:
            raise Exception(f"x_54 was equal {x_54}, but expected it to be equal to assertion: {self.assertion}")
