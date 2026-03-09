from metamath2py.classes.ps_ch_ta_from_ph import ps_ch_ta_from_ph

class ps_ch_ta_from_ph_proof(ps_ch_ta_from_ph):
    def proof(self):
        x_1 = self.e_imp_ps_ch_th
        x_2 = self.e_imp_ph_th_ta
        x_3 = self.e_ph_true
        x_4 = OWSI().call({"ph":"ph","ps":"(th -> ta)"},{"essential_1":x_3,"essential_2":x_2})
        if x_4 != self.assertion:
            raise Exception(f"x_4 was equal {x_4}, but expected it to be equal to assertion: {self.assertion}")
