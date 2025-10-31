from __future__ import annotations

import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from metamath_agent.offline_runner import generate_from_description
from verification import verify_proof
from paths import classes_folder_path, proofs_folder_path, PathsEnum


def _expected_new_name(base: str) -> str:
    # Mirror offline runner logic: append _ALT unless it already ends with _ALT.
    return base + "_X" if base.endswith("_ALT") else base + "_ALT"


def _stash_file(original: str, *, backup_root: str, suffix: str) -> str:
    """Copy a file into a temporary location, remove the original, and return the backup path."""
    stem, _ = os.path.splitext(os.path.basename(original))
    backup_path = os.path.join(backup_root, f"{stem}.{suffix}")
    if os.path.exists(original):
        shutil.copy2(original, backup_path)
    try:
        os.remove(original)
    except FileNotFoundError:
        pass
    return backup_path


@contextmanager
def temporarily_remove_theorem_files(theorem_name: str):
    """Temporarily remove a theorem's class/proof from the repo and restore after.

    - Copies the two files (class + proof) into a temp dir as backup.
    - Deletes them from the working tree to hide them from generation.
    - Yields (classes_dir, proofs_dir).
    - Restores the original files at the end regardless of test outcome.
    """

    classes_dir = classes_folder_path
    proofs_dir = proofs_folder_path

    class_file = os.path.join(classes_dir, f"{theorem_name}.py")
    proof_file = os.path.join(proofs_dir, f"{theorem_name}.py")

    tmp_mgr = TemporaryDirectory()
    backup_root = tmp_mgr.name
    backup_class: str = ""
    backup_proof: str = ""
    try:
        backup_class = _stash_file(
            class_file,
            backup_root=backup_root,
            suffix="class.py",
        )
        backup_proof = _stash_file(
            proof_file,
            backup_root=backup_root,
            suffix="proof.py",
        )

        yield classes_dir, proofs_dir
    finally:
        # Restore originals
        if backup_class and os.path.exists(backup_class):
            shutil.copy2(backup_class, class_file)
        if backup_proof and os.path.exists(backup_proof):
            shutil.copy2(backup_proof, proof_file)
        tmp_mgr.cleanup()


def test_rebuild_theorem_from_natural_language():
    # Inputs with defaults.
    theorem_name = "A0K0"
    description = "Description: Modus ponens combined with a double syllogism inference."

    # Reuse repository paths defined in paths.py
    src_classes = classes_folder_path
    src_proofs = proofs_folder_path

    # Resolve original file paths for later comparison output.
    original_class_path = os.path.join(src_classes, f"{theorem_name}.py")
    original_proof_path = os.path.join(src_proofs, f"{theorem_name}.py")
    assert os.path.exists(original_class_path), f"Missing original class file: {original_class_path}"
    assert os.path.exists(original_proof_path), f"Missing original proof file: {original_proof_path}"

    new_name = _expected_new_name(theorem_name)
    assert new_name != theorem_name

    gen_class_code = gen_proof_code = ""
    with temporarily_remove_theorem_files(theorem_name) as (
        tmp_classes,
        tmp_proofs,
    ):
        # Use the (offline) agent runner to generate class and proof from NL description.
        proofs_package = (
            f"{PathsEnum.metamath2py_folder_name.value}.{PathsEnum.proofs_folder_name.value}"
        )
        gen = generate_from_description(
            base_name=theorem_name,
            description=description,
            classes_dir=Path(tmp_classes),
            proofs_dir=Path(tmp_proofs),
            proofs_package=proofs_package,
        )
        assert gen.name == new_name

        # Remove any cached modules for the original package to avoid cross-contamination.
        pkg_root = PathsEnum.metamath2py_folder_name.value
        for mod in list(sys.modules):
            if mod == pkg_root or mod.startswith(f"{pkg_root}."):
                sys.modules.pop(mod, None)

        # Verify the newly generated proof using the verification helper.
        result = verify_proof(new_name)
        assert result.success, (
            f"Verification failed at stage {result.stage}: {result.error_message}\n"
            f"{result.traceback or ''}"
        )
        # Read back generated sources for comparison/printing.
        gen_class_path = os.path.join(tmp_classes, f"{new_name}.py")
        gen_proof_path = os.path.join(tmp_proofs, f"{new_name}.py")
        with open(gen_class_path, encoding="utf-8") as gen_class_file:
            gen_class_code = gen_class_file.read()
        with open(gen_proof_path, encoding="utf-8") as gen_proof_file:
            gen_proof_code = gen_proof_file.read()

    # Load original sources for comparison and output.
    with open(original_class_path, encoding="utf-8") as orig_class_file:
        orig_class_code = orig_class_file.read()
    with open(original_proof_path, encoding="utf-8") as orig_proof_file:
        orig_proof_code = orig_proof_file.read()

    # Print side-by-side summaries for human inspection after the test run.
    print("\n=== Original class (", theorem_name, ") ===\n", orig_class_code, sep="")
    print("\n=== Generated class (", new_name, ") ===\n", gen_class_code, sep="")
    print("\n=== Original proof (", theorem_name, ") ===\n", orig_proof_code, sep="")
    print("\n=== Generated proof (", new_name, ") ===\n", gen_proof_code, sep="")
