from metamath2py.classes.T_1PLUS1 import T_1PLUS1

class T_1PLUS1_proof(T_1PLUS1):
    def proof(self):
        step_1 = self.essential_2
        if step_1 != self.assertion:
            raise Exception(f"step_1 was equal {step_1}, but expected it to be equal to assertion: {self.assertion}")
