from __future__ import annotations

from typing import Iterable, Mapping

from examples.classes.A0K0 import A0K0
from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.theorem_state import RequiredTheoremPremises, TheoremState


def _split_items(raw: str) -> list[str]:
    items: list[str] = []
    for part in raw.replace(",", "\n").splitlines():
        value = part.strip()
        if value:
            items.append(value)
    return items


def parse_required_premises(raw: str) -> list[RequiredTheoremPremises]:
    premises: list[RequiredTheoremPremises] = []
    for line in raw.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        separator = ":" if ":" in trimmed else "="
        if separator not in trimmed:
            continue
        left, right = trimmed.split(separator, 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            premises.append(RequiredTheoremPremises(left=left, right=right))
    return premises


def parse_proof_steps(raw: str) -> list[ProofStep]:
    steps: list[ProofStep] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        comment = None
        if "#" in text:
            text, comment_part = text.split("#", 1)
            comment = comment_part.strip() or None

        if "|" in text:
            parts = [p.strip() for p in text.split("|")]
            left = parts[0] if parts else ""
            right = parts[1] if len(parts) > 1 else ""
            if not comment and len(parts) > 2:
                comment = parts[2] or None
        elif "=" in text:
            left, right = [p.strip() for p in text.split("=", 1)]
        elif ":" in text:
            left, right = [p.strip() for p in text.split(":", 1)]
        else:
            continue

        if left and right:
            steps.append(ProofStep(left=left, right=right, comment=comment))
    return steps


def build_node_from_form(form: Mapping[str, str]) -> Node:
    goal = (form.get("goal") or "").strip() or "Solve the theorem"
    theorem_label = (form.get("theorem_label") or "CustomTheorem").strip() or "CustomTheorem"
    floating_args = _split_items(form.get("floating_args") or "")
    essential_args = _split_items(form.get("essential_args") or "")
    assertion = (form.get("assertion") or "").strip()
    required_premises = parse_required_premises(form.get("required_premises") or "")
    proof_steps = parse_proof_steps(form.get("proof_steps") or "")

    theorem_state = TheoremState(
        label=theorem_label,
        floating_args=floating_args,
        essential_args=essential_args,
        required_theorem_premises=required_premises,
        assertion=assertion,
    )
    proof_state = ProofState(steps=proof_steps)

    task = CreateNodeTask(
        goal=goal,
        theorem=theorem_state,
        proof=proof_state,
    )
    return Node(created_node_task=task)


def build_default_root_node() -> Node:
    """Demo root node with partial A0K0 proof to visualize immediately."""
    base = A0K0()
    floating = ["ph", "ps", "ch", "th", "ta"]
    essential = ["essential_1", "essential_2", "essential_3"]
    required = [
        RequiredTheoremPremises(left="essential_1", right=base.essential_1),
        RequiredTheoremPremises(left="essential_2", right=base.essential_2),
        RequiredTheoremPremises(left="essential_3", right=base.essential_3),
    ]
    theorem_state = TheoremState(
        label="A0K0_WEB_UI",
        floating_args=floating,
        essential_args=essential,
        required_theorem_premises=required,
        assertion=base.assertion,
    )
    steps = [
        ProofStep(left="x1", right='"wff ps"', comment=None),
        ProofStep(left="x2", right='"wff ph"', comment=None),
        ProofStep(left="x3", right='"wff ch"', comment=None),
        ProofStep(left="x4", right='"wff th"', comment=None),
        ProofStep(left="x5", right='"wff ta"', comment=None),
        ProofStep(left="x6", right='"wff ph"', comment=None),
        ProofStep(left="x7", right='"wff ps"', comment=None),
        ProofStep(left="x8", right=base.essential_1, comment="essential_1"),
        ProofStep(left="x9", right='"partial proof step"', comment="demo"),
        ProofStep(left="x10", right=base.essential_2, comment="essential_2"),
    ]
    proof_state = ProofState(steps=steps)
    task = CreateNodeTask(
        goal="Complete the A0K0 proof",
        theorem=theorem_state,
        proof=proof_state,
    )
    return Node(created_node_task=task)
