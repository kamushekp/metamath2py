from pathlib import Path

from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.theorem_state import RequiredTheoremPremises, TheoremState
from saplings.tools.theorem_recovery import TheoremRecoveryRunner


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _build_a0k0_states(label: str = "A0K0_TEMP") -> tuple[TheoremState, ProofState]:
    theorem_state = TheoremState(
        label=label,
        floating_args=["ph", "ps", "ch", "th", "ta"],
        essential_args=["essential_1", "essential_2", "essential_3"],
        required_theorem_premise_premises=[
            RequiredTheoremPremises(left="essential_1", right="|- ph"),
            RequiredTheoremPremises(left="essential_2", right="|- ( ps -> ( ch -> th ) )"),
            RequiredTheoremPremises(left="essential_3", right="|- ( ph -> ( th -> ta ) )"),
        ],
        assertion="|- ( ps -> ( ch -> ta ) )",
    )

    steps = [
        ProofStep(left="x_1", right='"wff ps"', comment=None),
        ProofStep(left="x_2", right='"wff ph"', comment=None),
        ProofStep(left="x_3", right='"wff ch"', comment=None),
        ProofStep(left="x_4", right='"wff th"', comment=None),
        ProofStep(left="x_5", right='"wff ta"', comment=None),
        ProofStep(left="x_6", right='"wff ph"', comment=None),
        ProofStep(left="x_7", right='"wff ps"', comment=None),
        ProofStep(left="x_8", right="self.essential_1", comment=None),
        ProofStep(
            left="x_9",
            right='VLEL().call({"ph": x_6, "ps": x_7}, {"essential_1": x_8})',
            comment=None,
        ),
        ProofStep(left="x_10", right="self.essential_2", comment=None),
        ProofStep(left="x_11", right="self.essential_3", comment=None),
        ProofStep(
            left="x_12",
            right=(
                'SW6P().call({"ph": x_1, "ps": x_2, "ch": x_3, "th": x_4, "ta": x_5}, '
                '{"essential_1": x_9, "essential_2": x_10, "essential_3": x_11})'
            ),
            comment=None,
        ),
    ]
    return theorem_state, ProofState(steps=steps)


def test_recover_theorem_data_matches_a0k0_files():
    theorem_state, proof_state = _build_a0k0_states(label="A0K0")
    runner = TheoremRecoveryRunner(theorem_state, proof_state)

    class_source, proof_source = runner.recover_theorem_data()

    expected_class = Path("metamath2py/classes/A0K0.py").read_text()
    expected_proof = Path("metamath2py/proofs/A0K0.py").read_text()

    assert _normalize(class_source) == _normalize(expected_class)
    assert _normalize(proof_source) == _normalize(expected_proof)


def test_verify_positive_result():
    theorem_state, proof_state = _build_a0k0_states(label="A0K0_TEMP_OK")
    runner = TheoremRecoveryRunner(theorem_state, proof_state)

    result = runner.verify()

    assert result.success is True
    assert result.stage == "success"


def test_verify_fails_when_last_step_missing():
    theorem_state, proof_state = _build_a0k0_states(label="A0K0_TEMP_FAIL")
    truncated_steps = ProofState(steps=proof_state.steps[:-1])
    runner = TheoremRecoveryRunner(theorem_state, truncated_steps)

    result = runner.verify()

    assert result.success is False
    assert result.stage == "execution"
