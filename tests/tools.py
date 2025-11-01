from __future__ import annotations

import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Tuple

from paths import PathsEnum, classes_folder_path, proofs_folder_path, src_classes, src_proofs


def expected_new_name(base: str) -> str:
    """Mirror offline runner logic: append _ALT unless it already ends with _ALT."""
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
def temporarily_remove_theorem_files(theorem_name: str) -> Iterator[Tuple[Path, Path]]:
    """Temporarily remove a theorem's class/proof from the repo and restore after.

    - Copies the two files (class + proof) into a temp dir as backup.
    - Deletes them from the working tree to hide them from generation.
    - Yields (classes_dir, proofs_dir).
    - Restores the original files at the end regardless of test outcome.
    """

    classes_dir = Path(classes_folder_path)
    proofs_dir = Path(proofs_folder_path)

    class_file = classes_dir / f"{theorem_name}.py"
    proof_file = proofs_dir / f"{theorem_name}.py"

    tmp_mgr = TemporaryDirectory()
    backup_root = tmp_mgr.name
    backup_class = ""
    backup_proof = ""
    try:
        backup_class = _stash_file(
            str(class_file),
            backup_root=backup_root,
            suffix="class.py",
        )
        backup_proof = _stash_file(
            str(proof_file),
            backup_root=backup_root,
            suffix="proof.py",
        )

        yield classes_dir, proofs_dir
    finally:
        if backup_class and os.path.exists(backup_class):
            shutil.copy2(backup_class, class_file)
        if backup_proof and os.path.exists(backup_proof):
            shutil.copy2(backup_proof, proof_file)
        tmp_mgr.cleanup()


def clear_metamath2py_modules() -> None:
    """Drop cached metamath2py.* modules to avoid leaking state between tests."""
    pkg_root = PathsEnum.metamath2py_folder_name.value
    for mod in list(sys.modules):
        if mod == pkg_root or mod.startswith(f"{pkg_root}."):
            sys.modules.pop(mod, None)


def ensure_original_theorem_files(theorem_name: str) -> Tuple[Path, Path]:
    """Return original class and proof paths, asserting they exist."""
    class_path = src_classes / f"{theorem_name}.py"
    proof_path = src_proofs / f"{theorem_name}.py"
    assert class_path.exists(), f"Missing original class file: {class_path}"
    assert proof_path.exists(), f"Missing original proof file: {proof_path}"
    return class_path, proof_path
