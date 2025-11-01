from __future__ import annotations

from metamath_agent.offline_runner import generate_from_description
from paths import PathsEnum
from tests.tools import (
    clear_metamath2py_modules,
    expected_new_name,
    ensure_original_theorem_files,
    temporarily_remove_theorem_files,
)
from verification import verify_proof


def test_rebuild_theorem_from_natural_language():
    theorem_name = "A0K0"
    description = "Description: Modus ponens combined with a double syllogism inference."

    original_class_path, original_proof_path = ensure_original_theorem_files(theorem_name)

    new_name = expected_new_name(theorem_name)
    assert new_name != theorem_name

    gen_class_code = gen_proof_code = ""
    with temporarily_remove_theorem_files(theorem_name) as (
        tmp_classes,
        tmp_proofs,
    ):
        proofs_package = (
            f"{PathsEnum.metamath2py_folder_name.value}.{PathsEnum.proofs_folder_name.value}"
        )
        gen = generate_from_description(
            base_name=theorem_name,
            description=description,
            classes_dir=tmp_classes,
            proofs_dir=tmp_proofs,
            proofs_package=proofs_package,
        )
        assert gen.name == new_name

        clear_metamath2py_modules()

        result = verify_proof(new_name)
        assert result.success, (
            f"Verification failed at stage {result.stage}: {result.error_message}\n"
            f"{result.traceback or ''}"
        )

        gen_class_code = (tmp_classes / f"{new_name}.py").read_text(encoding="utf-8")
        gen_proof_code = (tmp_proofs / f"{new_name}.py").read_text(encoding="utf-8")

    orig_class_code = original_class_path.read_text(encoding="utf-8")
    orig_proof_code = original_proof_path.read_text(encoding="utf-8")

    print("\n=== Original class (", theorem_name, ") ===\n", orig_class_code, sep="")
    print("\n=== Generated class (", new_name, ") ===\n", gen_class_code, sep="")
    print("\n=== Original proof (", theorem_name, ") ===\n", orig_proof_code, sep="")
    print("\n=== Generated proof (", new_name, ") ===\n", gen_proof_code, sep="")
