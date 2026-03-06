from metamath2py.classes.ps_ch_imp_ta_from_ph_and_implications import ps_ch_imp_ta_from_ph_and_implications

class ps_ch_imp_ta_from_ph_and_implications_proof(ps_ch_imp_ta_from_ph_and_implications):
    def proof(self):
        x_1 = SomeTheorem().call({"ps": x_1}, {"essential_2": self.essential_2})
        x_2 = SomeTheorem().call({"ch": x_2}, {"essential_2": x_1})
        x_3 = SomeTheorem().call({"ph": self.essential_1}, {"essential_3": self.essential_3})
        x_4 = SomeTheorem().call({"th": x_2}, {"essential_1": x_3})
        x_5 = SomeTheorem().call({"th": x_2}, {"essential_1": x_3})
        if x_5 != self.assertion:
            raise Exception(f"x_5 was equal {x_5}, but expected it to be equal to assertion: {self.assertion}")
