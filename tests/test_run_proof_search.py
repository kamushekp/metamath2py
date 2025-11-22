from __future__ import annotations

from pathlib import Path

from metamath_agent.agent import run_proof_search
from metamath_agent.config import AgentConfig
from paths import PathsEnum
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.generated_patch import GeneratedPatch
from saplings.dtos.trajectory_step import TrajectoryStep
from tests.tools import (
    clear_metamath2py_modules,
    expected_new_name,
    ensure_original_theorem_files,
    temporarily_remove_theorem_files,
)
from verification import verify_proof


def test_run_proof_search_rebuilds_theorem(monkeypatch):
    theorem_name = "A0K0"
    description = "Description: Modus ponens combined with a double syllogism inference."

    original_class_path, original_proof_path = ensure_original_theorem_files(theorem_name)

    generated_name = None
    expected_name = expected_new_name(theorem_name)

    run_path: Path | None = None

    with temporarily_remove_theorem_files(theorem_name) as (
        tmp_classes,
        tmp_proofs,
    ):
        def fake_build_agent(_cfg):
            class StubAgent:
                def run_iter(self_inner, goal: str):
                    nonlocal generated_name
                    from metamath_agent.offline_runner import generate_from_description

                    proofs_package = (
                        f"{PathsEnum.metamath2py_folder_name.value}."
                        f"{PathsEnum.proofs_folder_name.value}"
                    )
                    gen = generate_from_description(
                        base_name=theorem_name,
                        description=goal,
                        classes_dir=tmp_classes,
                        proofs_dir=tmp_proofs,
                        proofs_package=proofs_package,
                    )
                    generated_name = gen.name
                    task = Task.from_goal(goal)
                    result = GeneratedPatch(
                        summary=f"Stub proof found for {goal}",
                        used_theorems=[],
                        terminal=True,
                    )
                    trajectory = [TrajectoryStep(task=task, result=result)]
                    yield trajectory, 1.0, True

            return StubAgent()

        monkeypatch.setattr("metamath_agent.agent.build_agent", fake_build_agent)

        cfg = AgentConfig()
        trajectory, score, is_solution = run_proof_search(description, cfg)

        assert is_solution is True
        assert score == 1.0
        assert trajectory and trajectory[0].result.summary.startswith("Stub proof found")
        assert generated_name == expected_name
        assert (tmp_classes / f"{generated_name}.py").exists()
        assert (tmp_proofs / f"{generated_name}.py").exists()
        # No logging artifacts expected

        clear_metamath2py_modules()
        result = verify_proof(generated_name)
        assert result.success, (
            f"Verification failed at stage {result.stage}: {result.error_message}\n"
            f"{result.traceback or ''}"
        )

        gen_class_code = (tmp_classes / f"{generated_name}.py").read_text(encoding="utf-8")
        gen_proof_code = (tmp_proofs / f"{generated_name}.py").read_text(encoding="utf-8")

    orig_class_code = original_class_path.read_text(encoding="utf-8")
    orig_proof_code = original_proof_path.read_text(encoding="utf-8")

    print("\n=== Original class (", theorem_name, ") ===\n", orig_class_code, sep="")
    print("\n=== Generated class (", generated_name, ") ===\n", gen_class_code, sep="")
    print("\n=== Original proof (", theorem_name, ") ===\n", orig_proof_code, sep="")
    print("\n=== Generated proof (", generated_name, ") ===\n", gen_proof_code, sep="")
