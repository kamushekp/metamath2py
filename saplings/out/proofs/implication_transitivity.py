from metamath2py.classes.implication_transitivity import implication_transitivity

class implication_transitivity_proof(implication_transitivity):
    def proof(self):
        _ = self.essential_1
        _ = self.essential_2
        _ = "wff ph"
        if _ != self.assertion:
            raise Exception(f"_ was equal {_}, but expected it to be equal to assertion: {self.assertion}")
