from __future__ import annotations

import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from metamath_agent.offline_runner import generate_from_description
from verification import verify_proof


def _expected_new_name(base: str) -> str:
    # Mirror offline runner logic: append _ALT unless it already ends with _ALT.
    return base + "_X" if base.endswith("_ALT") else base + "_ALT"


@contextmanager
def temporarily_remove_theorem_files(theorem_name: str, project_root: Path):
    """Temporarily remove a theorem's class/proof from the repo and restore after.

    - Copies the two files (class + proof) into a temp dir as backup.
    - Deletes them from the working tree to hide them from generation.
    - Yields (classes_dir, proofs_dir).
    - Restores the original files at the end regardless of test outcome.
    """
    classes_dir = project_root / "metamath2py" / "classes"
    proofs_dir = project_root / "metamath2py" / "proofs"

    class_file = classes_dir / f"{theorem_name}.py"
    proof_file = proofs_dir / f"{theorem_name}.py"

    tmp_mgr = TemporaryDirectory()
    backup_root = Path(tmp_mgr.name)
    backup_class = backup_root / f"{theorem_name}.class.py"
    backup_proof = backup_root / f"{theorem_name}.proof.py"

    try:
        # Backup originals if present
        if class_file.exists():
            shutil.copy2(class_file, backup_class)
        if proof_file.exists():
            shutil.copy2(proof_file, backup_proof)

        # Remove from the tree
        try:
            class_file.unlink()
        except FileNotFoundError:
            pass
        try:
            proof_file.unlink()
        except FileNotFoundError:
            pass

        yield classes_dir, proofs_dir
    finally:
        # Restore originals
        if backup_class.exists():
            shutil.copy2(backup_class, class_file)
        if backup_proof.exists():
            shutil.copy2(backup_proof, proof_file)
        tmp_mgr.cleanup()


def test_rebuild_theorem_from_natural_language():
    # Inputs with defaults.
    theorem_name = "A0K0"
    description = "Description: Modus ponens combined with a double syllogism inference."

    project_root = Path(__file__).resolve().parents[1]
    src_pkg = project_root / "metamath2py"
    src_classes = src_pkg / "classes"
    src_proofs = src_pkg / "proofs"

    # Resolve original file paths for later comparison output.
    original_class_path = src_classes / f"{theorem_name}.py"
    original_proof_path = src_proofs / f"{theorem_name}.py"
    assert original_class_path.exists(), f"Missing original class file: {original_class_path}"
    assert original_proof_path.exists(), f"Missing original proof file: {original_proof_path}"

    new_name = _expected_new_name(theorem_name)
    assert new_name != theorem_name

    gen_class_code = gen_proof_code = ""
    with temporarily_remove_theorem_files(theorem_name, project_root) as (
        tmp_classes,
        tmp_proofs,
    ):
        # Use the (offline) agent runner to generate class and proof from NL description.
        gen = generate_from_description(
            base_name=theorem_name,
            description=description,
            classes_dir=tmp_classes,
            proofs_dir=tmp_proofs,
            proofs_package="metamath2py.proofs",
        )
        assert gen.name == new_name

        # Remove any cached modules for the original package to avoid cross-contamination.
        for mod in list(sys.modules):
            if mod == "metamath2py" or mod.startswith("metamath2py."):
                sys.modules.pop(mod, None)

        # Verify the newly generated proof using the verification helper.
        result = verify_proof(new_name, package="metamath2py.proofs")
        assert result.success, (
            f"Verification failed at stage {result.stage}: {result.error_message}\n"
            f"{result.traceback or ''}"
        )
        # Read back generated sources for comparison/printing.
        gen_class_code = (tmp_classes / f"{new_name}.py").read_text(encoding="utf-8")
        gen_proof_code = (tmp_proofs / f"{new_name}.py").read_text(encoding="utf-8")

    # Load original sources for comparison and output.
    orig_class_code = original_class_path.read_text(encoding="utf-8")
    orig_proof_code = original_proof_path.read_text(encoding="utf-8")

    # Ensure we did not recreate an exact copy of the removed theorem.
    assert gen_class_code != orig_class_code, "Generated class matches the original exactly; expected differences"
    assert gen_proof_code != orig_proof_code, "Generated proof matches the original exactly; expected differences"

    # Print side-by-side summaries for human inspection after the test run.
    print("\n=== Original class (", theorem_name, ") ===\n", orig_class_code, sep="")
    print("\n=== Generated class (", new_name, ") ===\n", gen_class_code, sep="")
    print("\n=== Original proof (", theorem_name, ") ===\n", orig_proof_code, sep="")
    print("\n=== Generated proof (", new_name, ") ===\n", gen_proof_code, sep="")
