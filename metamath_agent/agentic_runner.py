from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

from paths import classes_folder_path, proofs_folder_path
from saplings.dtos.node import Node
from saplings.dtos.search_result import SearchResult
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.saplings_agents.a_star import AStar
from saplings.tools.theorem_recovery import TheoremRecoveryRunner
from verification import ProofCheckResult, verify_proof


@contextmanager
def _temporarily_hide_theorem_files(theorem_name: str | None) -> Iterator[None]:
    if not theorem_name:
        yield
        return

    classes_path = Path(classes_folder_path)
    proofs_path = Path(proofs_folder_path)
    class_file = classes_path / f"{theorem_name}.py"
    proof_file = proofs_path / f"{theorem_name}.py"

    with TemporaryDirectory() as tmp_dir:
        backup_dir = Path(tmp_dir)
        moved: list[tuple[Path, Path]] = []
        for original in (class_file, proof_file):
            if not original.exists():
                continue
            backup = backup_dir / f"{original.parent.name}__{original.name}"
            shutil.copy2(original, backup)
            original.unlink()
            moved.append((original, backup))
        try:
            yield
        finally:
            for original, backup in moved:
                if backup.exists():
                    shutil.copy2(backup, original)


def _set_retrieval_block(theorems: list[str]) -> None:
    blocked = [name.strip() for name in theorems if name.strip()]
    if not blocked:
        return
    os.environ["SAPLINGS_BLOCK_THEOREMS"] = ",".join(blocked)


def _materialize_task(output_name: str, task: CreateNodeTask, classes_dir: Path, proofs_dir: Path) -> None:
    theorem_state = copy.deepcopy(task.theorem)
    theorem_state.label = output_name

    runner = TheoremRecoveryRunner(theorem_state, task.proof)
    class_source, proof_source = runner.recover_theorem_data(unique_label=output_name)

    classes_dir.mkdir(parents=True, exist_ok=True)
    proofs_dir.mkdir(parents=True, exist_ok=True)
    (classes_dir / f"{output_name}.py").write_text(class_source, encoding="utf-8")
    (proofs_dir / f"{output_name}.py").write_text(proof_source, encoding="utf-8")


def _best_task_from_result(root: Node, result: SearchResult) -> CreateNodeTask:
    if result.trajectory:
        return result.trajectory[-1].task_after
    return root.created_node_task


def _is_materializable_task(task: CreateNodeTask) -> bool:
    theorem = task.theorem
    if not theorem.label.strip():
        return False
    if not theorem.assertion.strip():
        return False
    if not theorem.essential_args:
        return False
    if not theorem.required_theorem_premises:
        return False
    if not task.proof.steps:
        return False
    return True


def run_agentic_recovery(
    *,
    description: str,
    output_name: str,
    requested_patch_sets: int,
    max_depth: int,
    step_max_turns: int,
    blocked_theorems: list[str],
    hide_local_theorem: str | None,
    enable_benchmark_priors: bool,
    verify_generated: bool,
) -> tuple[SearchResult, ProofCheckResult | None]:
    os.environ.setdefault("SAPLINGS_ENABLE_ONLINE_GENERATION", "1")
    if enable_benchmark_priors:
        os.environ["SAPLINGS_ENABLE_BENCHMARK_PRIORS"] = "1"
    _set_retrieval_block(blocked_theorems)

    root_task = CreateNodeTask.from_goal(description)
    root_node = Node(created_node_task=root_task)
    search = AStar(
        requested_patch_sets=requested_patch_sets,
        max_depth=max_depth,
        step_max_turns=step_max_turns,
    )

    with _temporarily_hide_theorem_files(hide_local_theorem):
        result = search.run(root_node)
        best_task = _best_task_from_result(root_node, result)
        if not _is_materializable_task(best_task):
            raise RuntimeError(
                "Search finished without a materializable theorem/proof. "
                "Increase --max-depth and/or --requested-patch-sets."
            )
        _materialize_task(
            output_name=output_name,
            task=best_task,
            classes_dir=Path(classes_folder_path),
            proofs_dir=Path(proofs_folder_path),
        )

    if not verify_generated:
        return result, None

    verify_result = verify_proof(output_name)
    return result, verify_result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agentic theorem recovery with A* + retrieval context (without direct theorem file retrieval)."
    )
    parser.add_argument("--description", required=True, help="Natural-language theorem goal.")
    parser.add_argument("--output-name", required=True, help="Name of generated theorem module.")
    parser.add_argument(
        "--requested-patch-sets",
        type=int,
        default=3,
        help="Branching factor: candidates generated per expansion.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="Maximum A* depth from root node.",
    )
    parser.add_argument(
        "--step-max-turns",
        type=int,
        default=8,
        help="Max turns per LLM call inside candidate generation.",
    )
    parser.add_argument(
        "--block-theorem",
        action="append",
        default=[],
        help="Theorem id to exclude from retrieval (repeatable). Example: --block-theorem A0K0",
    )
    parser.add_argument(
        "--hide-local-theorem",
        default=None,
        help="Temporarily remove theorem files from metamath2py/classes|proofs during run.",
    )
    parser.add_argument(
        "--enable-benchmark-priors",
        action="store_true",
        help="Enable deterministic benchmark priors (currently for A0K0-style goal).",
    )
    parser.add_argument("--no-verify", action="store_true", help="Skip verification of generated output.")
    return parser


def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        result, verify_result = run_agentic_recovery(
            description=args.description,
            output_name=args.output_name,
            requested_patch_sets=args.requested_patch_sets,
            max_depth=args.max_depth,
            step_max_turns=args.step_max_turns,
            blocked_theorems=args.block_theorem,
            hide_local_theorem=args.hide_local_theorem,
            enable_benchmark_priors=args.enable_benchmark_priors,
            verify_generated=not args.no_verify,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False))
        return 1

    payload = {
        "is_solution_node": result.is_solution,
        "trajectory_length": len(result.trajectory),
        "node_score": {
            "score": result.node_score.score,
            "depth": result.node_score.depth,
            "verify_progress": result.node_score.verify_progress,
            "stage": result.node_score.stage.value,
            "reasoning": result.node_score.reasoning,
        },
    }
    if verify_result is not None:
        payload["verify"] = {
            "success": verify_result.success,
            "stage": verify_result.stage.value,
            "error_message": verify_result.error_message,
        }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if verify_result is not None and not verify_result.success:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
