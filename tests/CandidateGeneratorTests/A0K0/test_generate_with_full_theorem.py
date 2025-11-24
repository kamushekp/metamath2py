from __future__ import annotations

import sys
from pathlib import Path

from saplings.dtos.proof_state import EmptyProofState

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SITE_PACKAGES = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
for runtime_path in (PROJECT_ROOT, SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)

from metamath2py.classes.A0K0 import A0K0
from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
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


def test_generate_with_full_theorem():
    base = A0K0()
    theorem_state = _build_theorem_state()
    task = CreateNodeTask(goal="Populate proof for theorem A0K0", theorem=theorem_state, proof=EmptyProofState)
    node = Node(created_node_task=task)
    generator = CandidateGenerator()
    transitions = generator.generate(node)
    print(transitions)
