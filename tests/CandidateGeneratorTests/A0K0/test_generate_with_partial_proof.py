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
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.theorem_state import TheoremState
from saplings.dtos.tasks.create_node_task import CreateNodeTask


def _build_theorem_state() -> TheoremState:
    base = A0K0()
    floating = ["ph", "ps", "ch", "th", "ta"]
    essential = ["essential_1", "essential_2", "essential_3"]
    return TheoremState(
        label="A0K0",
        floating_args=floating,
        essential_args=essential,
        essential_theorems=["VLEL", "SW6P"],
        assertion=base.assertion,
    )


def _first_step(base: A0K0) -> ProofStep:
    return ProofStep(
        left="VLEL",
        right=base.essential_1,
        comment="Seed helper assertion",
    )


def test_generate_with_partial_proof():
    base = A0K0()
    theorem_state = _build_theorem_state()
    first_step = _first_step(base)
    current_proof = ProofState(steps=[first_step])
    task = CreateNodeTask(
        "Complete the remainder of the proof for A0K0",
        theorem=theorem_state,
        proof=current_proof,
    )
    node = Node(created_node_task=task)
    generator = CandidateGenerator()
    transitions = generator.generate(node)
    print(transitions)
