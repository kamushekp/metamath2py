from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SITE_PACKAGES = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
for runtime_path in (PROJECT_ROOT, SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)

from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.dtos.tasks.create_node_task import CreateNodeTask


def _make_description_task() -> Node:
    description = "Modus ponens combined with a double syllogism inference."
    task = CreateNodeTask.from_goal(description)
    return Node(task=task)


def test_generate_from_description():
    node = _make_description_task()
    generator = CandidateGenerator(b_factor=1, step_max_turns=1)
    transitions = generator.generate(node, n=1)
    print(transitions)
