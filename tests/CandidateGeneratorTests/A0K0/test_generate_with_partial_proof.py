from __future__ import annotations

import sys
from pathlib import Path

from examples.classes.A0K0 import A0K0
from metamath2py.classes.VLEL import VLEL

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SITE_PACKAGES = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
for runtime_path in (PROJECT_ROOT, SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)

from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.theorem_state import RequiredTheorem, TheoremState
from saplings.dtos.tasks.create_node_task import CreateNodeTask


def _build_theorem_state() -> TheoremState:
    base = A0K0()
    floating = ["ph", "ps", "ch", "th", "ta"]
    essential = ["essential_1", "essential_2", "essential_3"]
    required = [
        RequiredTheorem(left="essential_1", right=base.essential_1),
        RequiredTheorem(left="essential_2", right=base.essential_2),
        RequiredTheorem(left="essential_3", right=base.essential_3),
    ]
    return TheoremState(
        label="A0K0",
        floating_args=floating,
        essential_args=essential,
        required_theorems=required,
        assertion=base.assertion,
    )


def _partial_proof(base: A0K0) -> ProofState:
    """First 10 steps of examples/proofs/A0K0.py, stopping before essential_3."""
    vlel = VLEL()
    steps = [
        ProofStep(left="x1", right="wff ps", comment="floating ps"),
        ProofStep(left="x2", right="wff ph", comment="floating ph"),
        ProofStep(left="x3", right="wff ch", comment="floating ch"),
        ProofStep(left="x4", right="wff th", comment="floating th"),
        ProofStep(left="x5", right="wff ta", comment="floating ta"),
        ProofStep(left="x6", right="wff ph", comment="duplicate ph for VLEL"),
        ProofStep(left="x7", right="wff ps", comment="duplicate ps for VLEL"),
        ProofStep(left="x8", right=base.essential_1, comment="essential_1"),
        ProofStep(left="x9", right=vlel.assertion, comment="VLEL application"),
        ProofStep(left="x10", right=base.essential_2, comment="essential_2"),
    ]
    return ProofState(steps=steps)


def test_generate_with_partial_proof():
    base = A0K0()
    theorem_state = _build_theorem_state()
    current_proof = _partial_proof(base)
    task = CreateNodeTask(
        "Complete the remainder of the proof for A0K0",
        theorem=theorem_state,
        proof=current_proof,
    )
    node = Node(created_node_task=task)
    generator = CandidateGenerator()
    transitions = list(generator.generate(node))
    print(transitions)
