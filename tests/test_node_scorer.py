from __future__ import annotations

from examples.classes.A0K0 import A0K0
from metamath2py.classes.VLEL import VLEL

from saplings.node_scorer import NodeScorer
from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.theorem_state import RequiredTheorem, TheoremState


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
        label="A0K0_TEMP_SCORE",
        floating_args=floating,
        essential_args=essential,
        required_theorems=required,
        assertion=base.assertion,
    )


def _partial_proof_missing_last() -> ProofState:
    base = A0K0()
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


def _full_proof_state() -> ProofState:
    base = A0K0()
    vlel = VLEL()

    steps = [
        ProofStep(left="x1", right="wff ps", comment=None),
        ProofStep(left="x2", right="wff ph", comment=None),
        ProofStep(left="x3", right="wff ch", comment=None),
        ProofStep(left="x4", right="wff th", comment=None),
        ProofStep(left="x5", right="wff ta", comment=None),
        ProofStep(left="x6", right="wff ph", comment=None),
        ProofStep(left="x7", right="wff ps", comment=None),
        ProofStep(left="x8", right="self.essential_1", comment=None),
        ProofStep(
            left="x9",
            right='VLEL().call({"ph": x6, "ps": x7}, {"essential_1": x8})',
            comment=None,
        ),
        ProofStep(left="x10", right="self.essential_2", comment=None),
        ProofStep(left="x11", right="self.essential_3", comment=None),
    ]
    return ProofState(steps=steps)


def test_node_scorer_assigns_higher_score_to_more_complete_proof():
    theorem_state = _build_theorem_state()

    partial_task = CreateNodeTask(
        goal="Score partial proof",
        theorem=theorem_state,
        proof=_partial_proof_missing_last(),
    )
    full_task = CreateNodeTask(
        goal="Score full proof",
        theorem=theorem_state,
        proof=_full_proof_state(),
    )

    root_node = Node(created_node_task=partial_task)
    full_node = Node(created_node_task=full_task, parent_node=root_node)

    scorer = NodeScorer()
    partial_score = scorer.score(root_node)
    full_score = scorer.score(full_node)

    assert full_score.score > partial_score.score

