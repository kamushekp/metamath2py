from metamath2py.classes.A3AMB import A3AMB
from metamath2py.classes.OT69 import OT69
from metamath2py.classes.G05P import G05P
from metamath2py.classes.N3UC import N3UC
from metamath2py.classes.XPKSU import XPKSU
from metamath2py.classes.BI18H import BI18H

class A3AMB_proof(A3AMB):
    def proof(self):
        x_1 = "wff ch"
        x_2 = "wff ch"
        x_3 = "wff ph"
        x_4 = "wff ps"
        x_5 = XPKSU().call({"ph": x_2, "ps": x_3, "ch": x_4}, {})
        x_6 = "wff ph"
        x_7 = N3UC().call({"ph": x_5, "ps": x_6}, {})
        x_8 = "wff th"
        x_9 = "wff ch"
        x_10 = "wff ph"
        x_11 = "wff ps"
        x_12 = BI18H().call({"ph": x_9, "ps": x_10, "ch": x_11}, {})
        x_13 = "wff ch"
        x_14 = "wff ph"
        x_15 = "wff ps"
        x_16 = XPKSU().call({"ph": x_13, "ps": x_14, "ch": x_15}, {})
        x_17 = "wff ph"
        x_18 = N3UC().call({"ph": x_16, "ps": x_17}, {})
        x_19 = "wff ta"
        x_20 = "wff th"
        x_21 = self.essential_2
        x_22 = self.essential_1
        x_23 = OT69().call({"ph": x_18, "ps": x_19, "ch": x_20}, {"essential_1": x_21, "essential_2": x_22})
        x_24 = G05P().call({"ph": x_1, "ps": x_7, "ch": x_8}, {"essential_1": x_12, "essential_2": x_23})

        if x_24 != self.assertion:
            raise Exception(f"x_24 was equal {x_24}, but expected it to be equal to assertion: {self.assertion}")
