from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from llm_authoring import AuthoringWorkspace


@dataclass
class GenerationResult:
    name: str
    class_path: Path
    proof_path: Path


def _unique_name(base: str) -> str:
    if not base:
        return "A_GEN"
    if base.endswith("_ALT"):
        return base + "_X"
    return base + "_ALT"


def generate_from_description(
    *,
    base_name: str,
    description: str,
    classes_dir: Path,
    proofs_dir: Path,
    proofs_package: str = "metamath2py.proofs",
) -> GenerationResult:
    """
    Offline, deterministic agent runner that materializes a theorem class and
    a proof from a natural-language description. Intended for test usage where
    external LLMs and search backends are unavailable.

    The generated assertion is synthetic and only serves to exercise the full
    write/verify pipeline; it is not meant to mirror the removed theorem.
    """

    name = _unique_name(base_name)

    ws = AuthoringWorkspace(
        classes_dir=classes_dir,
        proofs_dir=proofs_dir,
        proofs_package=proofs_package,
    )

    # Build and save class (statement)
    stmt = ws.new_class(name)
    stmt.set_comment(description)
    # Minimal placeholder assertion; content is not critical for the test logic.
    stmt.set_assertion("|- ( ps -> ( ch -> ta ) )")
    stmt_res = stmt.save()
    if not stmt_res.success or not stmt_res.path:
        reasons = ", ".join(i.message for i in stmt_res.issues)
        raise RuntimeError(f"Failed to write class {name}: {reasons}")

    # Build and save a trivial proof that checks the assertion directly
    prf = ws.new_proof(name)
    # Assign last step to the assertion directly (no quoting via add_constant).
    prf.add_body_line("        x_1 = self.assertion")
    prf.set_last_step("x_1")
    prf_res = prf.save()
    if not prf_res.success or not prf_res.path:
        reasons = ", ".join(i.message for i in prf_res.issues)
        raise RuntimeError(f"Failed to write proof {name}: {reasons}")

    return GenerationResult(name=name, class_path=stmt_res.path, proof_path=prf_res.path)
