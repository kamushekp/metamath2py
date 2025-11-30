from __future__ import annotations

import os

os.environ['OPENAI_API_KEY']='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'
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SITE_PACKAGES = [
    PROJECT_ROOT / "venv" / "Lib" / "site-packages",  # Windows venv layout
    PROJECT_ROOT / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    PROJECT_ROOT / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
]
for runtime_path in (PROJECT_ROOT, *SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)

from examples.classes.A0K0 import A0K0
from metamath2py.classes.VLEL import VLEL

from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.tasks.patches.patch_proof_state_op import PatchProofStateOp
from saplings.dtos.tasks.patches.patch_set import PatchSet
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
    steps = _partial_proof(base).steps

    root_task = CreateNodeTask(
        "Complete the remainder of the proof for A0K0",
        theorem=theorem_state,
        proof=ProofState(steps=[]),
    )
    root_node = Node(created_node_task=root_task)

    current_node = root_node
    for idx, step in enumerate(steps, start=1):
        patch = PatchSet(
            change_description=f"Add proof step {idx}: {step.comment}",
            next_step_ideas="Keep extending the A0K0 proof by appending the next valid inference.",
            proof_ops=[
                PatchProofStateOp(
                    operation="insert",
                    left=step.left,
                    right=step.right,
                    comment=step.comment,
                )
            ],
        )
        next_task = patch.apply(current_node.created_node_task)
        current_node = Node(
            created_node_task=next_task,
            parent_node=current_node,
            created_from_patch_set=patch,
        )

    node = current_node
    generator = CandidateGenerator()
    transitions = list(generator.generate(node))
    print(transitions)
