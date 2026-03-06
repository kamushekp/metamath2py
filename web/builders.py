from __future__ import annotations

import os
from typing import Any, Mapping

from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.tasks.create_node_task import CreateNodeTask


def _coerce_env_int(name: str, *, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return max(minimum, default)
    try:
        value = int(raw)
    except ValueError:
        return max(minimum, default)
    return max(minimum, value)


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

        if "=" in text:
            left, right = [p.strip() for p in text.split("=", 1)]
        elif ":" in text:
            left, right = [p.strip() for p in text.split(":", 1)]
        elif "|" in text:
            parts = [p.strip() for p in text.split("|")]
            left = parts[0] if parts else ""
            right = parts[1] if len(parts) > 1 else ""
            if not comment and len(parts) > 2:
                comment = parts[2] or None
        else:
            continue

        if left and right:
            steps.append(ProofStep(left=left, right=right, comment=comment))
    return steps


def build_run_config_from_form(form: Mapping[str, str]) -> dict[str, Any]:
    _ = form
    requested_patch_sets = _coerce_env_int("SAPLINGS_REQUESTED_PATCH_SETS", default=2, minimum=1)
    max_depth = _coerce_env_int("SAPLINGS_MAX_DEPTH", default=13, minimum=1)
    step_max_turns = _coerce_env_int("SAPLINGS_STEP_MAX_TURNS", default=8, minimum=1)
    env_overrides: dict[str, str] = {
        "SAPLINGS_ENABLE_ONLINE_GENERATION": "1",
        "SAPLINGS_ENABLE_BENCHMARK_PRIORS": "0",
        "SAPLINGS_PRIMARY_MODEL": (os.getenv("SAPLINGS_PRIMARY_MODEL") or "gpt-5.2").strip(),
        "SAPLINGS_CHEAP_MODEL": (os.getenv("SAPLINGS_CHEAP_MODEL") or "gpt-5-mini").strip(),
        "SAPLINGS_BOOTSTRAP_MODEL": (os.getenv("SAPLINGS_BOOTSTRAP_MODEL") or "gpt-5-mini").strip(),
    }
    blocked = (os.getenv("SAPLINGS_BLOCK_THEOREMS") or "A0K0").strip()
    if blocked:
        env_overrides["SAPLINGS_BLOCK_THEOREMS"] = blocked
    for env_key in ("SAPLINGS_PROOF_MODEL_FALLBACKS", "SAPLINGS_BOOTSTRAP_MODEL_FALLBACKS", "SAPLINGS_MODEL_FALLBACKS"):
        value = (os.getenv(env_key) or "").strip()
        if value:
            env_overrides[env_key] = value

    return {
        "requested_patch_sets": requested_patch_sets,
        "max_depth": max_depth,
        "step_max_turns": step_max_turns,
        "env_overrides": env_overrides,
    }


def build_node_from_form(form: Mapping[str, str]) -> Node:
    goal = (form.get("goal") or "").strip() or "Solve the theorem from natural language."
    next_step_ideas = (form.get("next_step_ideas") or "").strip()
    proof_steps = parse_proof_steps(form.get("proof_steps") or "")
    task = CreateNodeTask.from_goal(goal)
    task.next_step_ideas = next_step_ideas
    if proof_steps:
        task.proof = ProofState(steps=proof_steps)
    return Node(created_node_task=task)


def build_node_and_run_config_from_form(form: Mapping[str, str]) -> tuple[Node, dict[str, Any]]:
    node = build_node_from_form(form)
    run_config = build_run_config_from_form(form)
    return node, run_config


def build_default_root_node() -> Node:
    """Default root starts from NL goal, so the graph shows full theorem bootstrap."""
    task = CreateNodeTask.from_goal("Modus ponens combined with a double syllogism inference.")
    return Node(created_node_task=task)
