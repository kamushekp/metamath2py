from metamath2py.classes.unprovable_P_eq_NP import unprovable_P_eq_NP

class unprovable_P_eq_NP_proof(unprovable_P_eq_NP):
    def proof(self):
        step_1 = self.essential_1
        step_2 = SoundnessImpliesNotProvable().call({"T": T, "ph": "P = NP"}, {"essential_1": self.essential_1})
        step_3 = self.essential_1
        if step_3 != self.assertion:
            raise Exception(f"step_3 was equal {step_3}, but expected it to be equal to assertion: {self.assertion}")
