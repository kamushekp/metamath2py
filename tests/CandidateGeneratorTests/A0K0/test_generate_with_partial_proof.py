from __future__ import annotations

import sys
from pathlib import Path

from examples.classes.A0K0 import A0K0

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SITE_PACKAGES = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
for runtime_path in (PROJECT_ROOT, SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)

from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.dtos.proof import ProofState, ProofStep, SymbolDecl, TheoremState
from saplings.dtos.tasks.task import Task


def _build_theorem_state() -> TheoremState:
    base = A0K0()
    floating = [
        SymbolDecl(name="ph", sort="wff"),
        SymbolDecl(name="ps", sort="wff"),
        SymbolDecl(name="ch", sort="wff"),
        SymbolDecl(name="th", sort="wff"),
        SymbolDecl(name="ta", sort="wff"),
    ]
    essential = [
        SymbolDecl(name="essential_1", annotation={"statement": base.essential_1}),
        SymbolDecl(name="essential_2", annotation={"statement": base.essential_2}),
        SymbolDecl(name="essential_3", annotation={"statement": base.essential_3}),
    ]
    return TheoremState(
        label="A0K0",
        floating_args=floating,
        essential_args=essential,
        essential_theorems=["VLEL", "SW6P"],
        assertion=base.assertion,
        metadata={"source": "examples/classes/A0K0.py"},
    )


def _first_step(base: A0K0) -> ProofStep:
    return ProofStep(
        reference="VLEL",
        substitutions={
            "ph": "ph",
            "ps": "ps",
            "essential_1": base.essential_1,
        },
        comment="Seed helper assertion",
    )


def test_generate_with_partial_proof():
    base = A0K0()
    theorem_state = _build_theorem_state()
    first_step = _first_step(base)
    current_proof = ProofState(steps=[first_step])
    task = Task.from_goal(
        "Complete the remainder of the proof for A0K0",
        theorem=theorem_state,
        proof=current_proof,
    )
    node = Node(task=task)
    generator = CandidateGenerator(b_factor=1, step_max_turns=1)
    transitions = generator.generate(node, n=1)
    print(transitions)
