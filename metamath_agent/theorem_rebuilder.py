from __future__ import annotations

import shutil
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Sequence

from .agent import run_proof_search
from .config import AgentConfig
from paths import PathsEnum, classes_folder_path, proofs_folder_path
from saplings.dtos import TrajectoryStep
from verification import ProofCheckResult, verify_proof


def _expected_new_name(base: str) -> str:
    """Mirror the offline runner logic: append _ALT unless already suffixed."""
    return base + "_X" if base.endswith("_ALT") else base + "_ALT"


def _clear_metamath_modules() -> None:
    """Drop cached metamath2py.* modules to avoid leaking state across runs."""
    pkg_root = PathsEnum.metamath2py_folder_name.value
    for mod in list(sys.modules):
        if mod == pkg_root or mod.startswith(f"{pkg_root}."):
            sys.modules.pop(mod, None)


def _ensure_original_files(theorem_name: str) -> tuple[Path, Path]:
    """Return the original class/proof paths for the theorem, ensuring they exist."""
    classes_dir = Path(classes_folder_path)
    proofs_dir = Path(proofs_folder_path)
    class_path = classes_dir / f"{theorem_name}.py"
    proof_path = proofs_dir / f"{theorem_name}.py"
    if not class_path.exists():
        raise FileNotFoundError(f"Missing original class file: {class_path}")
    if not proof_path.exists():
        raise FileNotFoundError(f"Missing original proof file: {proof_path}")
    return class_path, proof_path


def _stash_file(original: Path, *, backup_root: str, suffix: str) -> Path | None:
    """Copy a file into a temporary location, remove the original, and return the backup path."""
    if not original.exists():
        return None
    stem = original.stem
    backup_path = Path(backup_root) / f"{stem}.{suffix}"
    shutil.copy2(original, backup_path)
    try:
        original.unlink()
    except FileNotFoundError:
        pass
    return backup_path


@contextmanager
def _temporarily_remove_theorem_files(theorem_name: str) -> Iterator[tuple[Path, Path]]:
    """Temporarily remove the theorem's class/proof and restore them after the run."""
    classes_dir = Path(classes_folder_path)
    proofs_dir = Path(proofs_folder_path)

    class_file = classes_dir / f"{theorem_name}.py"
    proof_file = proofs_dir / f"{theorem_name}.py"

    tmp_mgr = TemporaryDirectory()
    backup_root = tmp_mgr.name
    backup_class: Path | None = None
    backup_proof: Path | None = None
    try:
        backup_class = _stash_file(class_file, backup_root=backup_root, suffix="class.py")
        backup_proof = _stash_file(proof_file, backup_root=backup_root, suffix="proof.py")
        yield classes_dir, proofs_dir
    finally:
        if backup_class and backup_class.exists():
            shutil.copy2(backup_class, class_file)
        if backup_proof and backup_proof.exists():
            shutil.copy2(backup_proof, proof_file)
        tmp_mgr.cleanup()


@dataclass
class RebuildOutcome:
    """Result of running a proof-search rebuild for a theorem."""

    original_class_path: Path
    original_proof_path: Path
    generated_class_path: Path
    generated_proof_path: Path
    original_class_code: str
    original_proof_code: str
    generated_class_code: str
    generated_proof_code: str
    new_name: str
    trajectory: Sequence[TrajectoryStep]
    score: float
    verification: ProofCheckResult


class ProofSearchRebuilder:
    """Helper that rebuilds a theorem by executing the live proof-search agent."""

    def __init__(self, theorem_name: str, goal: str, cfg: AgentConfig) -> None:
        self.theorem_name = theorem_name
        self.goal = goal
        self.cfg = cfg

    def rebuild(self) -> RebuildOutcome:
        original_class_path, original_proof_path = _ensure_original_files(self.theorem_name)
        new_name = _expected_new_name(self.theorem_name)
        if new_name == self.theorem_name:
            raise ValueError("Expected name must differ from the original theorem name.")

        with _temporarily_remove_theorem_files(self.theorem_name) as (classes_dir, proofs_dir):
            trajectory, score, is_solution = run_proof_search(self.goal, self.cfg)
            if not is_solution:
                raise RuntimeError("Proof search did not find a solution.")

            generated_class_path = classes_dir / f"{new_name}.py"
            generated_proof_path = proofs_dir / f"{new_name}.py"
            if not generated_class_path.exists():
                raise FileNotFoundError(f"Proof search did not produce class file: {generated_class_path}")
            if not generated_proof_path.exists():
                raise FileNotFoundError(f"Proof search did not produce proof file: {generated_proof_path}")

            _clear_metamath_modules()
            verification_result = verify_proof(new_name)
            if not verification_result.success:
                raise RuntimeError(
                    f"Verification failed at stage {verification_result.stage}: "
                    f"{verification_result.error_message}\n{verification_result.traceback or ''}"
                )

            generated_class_code = generated_class_path.read_text(encoding="utf-8")
            generated_proof_code = generated_proof_path.read_text(encoding="utf-8")

        original_class_code = original_class_path.read_text(encoding="utf-8")
        original_proof_code = original_proof_path.read_text(encoding="utf-8")

        return RebuildOutcome(
            original_class_path=original_class_path,
            original_proof_path=original_proof_path,
            generated_class_path=generated_class_path,
            generated_proof_path=generated_proof_path,
            original_class_code=original_class_code,
            original_proof_code=original_proof_code,
            generated_class_code=generated_class_code,
            generated_proof_code=generated_proof_code,
            new_name=new_name,
            trajectory=trajectory,
            score=score,
            verification=verification_result,
        )

if __name__ == '__main__':
    cfg = AgentConfig()
    rebuilder = ProofSearchRebuilder('A0K0', 'Modus ponens combined with a double syllogism inference.', cfg)
    rebuilder.rebuild()
