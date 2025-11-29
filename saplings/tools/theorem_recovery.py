from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from paths import classes_folder_path, proofs_folder_path
from saplings.dtos.proof_state import ProofState
from saplings.dtos.theorem_state import TheoremState
from verification import ProofCheckResult, verify_proof


class TheoremRecoveryRunner:
    """Recovers transient theorem/proof modules, verifies them, and cleans up."""

    def __init__(self, theorem_state: TheoremState, proof_state: ProofState):
        self.theorem_state = theorem_state
        self.proof_state = proof_state

    def recover_theorem_data(self) -> Tuple[str, str]:
        """Render Python source for the theorem class and its proof module."""

        label = self.theorem_state.label
        essential_lookup = {req.left: req.right for req in self.theorem_state.required_theorems}

        class_source = self._render_class_source(label, essential_lookup)
        proof_source = self._render_proof_source(label)
        return class_source, proof_source

    def _render_class_source(self, label: str, essential_lookup: dict[str, str]) -> str:
        lines: list[str] = []
        lines.append("from typing import TypedDict")
        lines.append("from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution")
        lines.append("")
        lines.append("")

        lines.append(f"class {label}_FloatingArgs(TypedDict):")
        for floating in self.theorem_state.floating_args:
            lines.append(f"    {floating}: str")
        lines.append("")
        lines.append("")

        lines.append(f"class {label}_EssentialArgs(TypedDict):")
        for essential in self.theorem_state.essential_args:
            lines.append(f"    {essential}: str")
        lines.append("")
        lines.append("")

        lines.append(f"class {label}:")
        lines.append(f"    def __init__(self):")
        for essential in self.theorem_state.essential_args:
            value = essential_lookup.get(essential, "")
            lines.append(f"        self.{essential} = {repr(value)}")
        lines.append("")
        lines.append(f"        self.assertion = {repr(self.theorem_state.assertion)}")
        lines.append("")
        lines.append(f"    def call(self, floatings: {label}_FloatingArgs, essentials: {label}_EssentialArgs):")
        for essential in self.theorem_state.essential_args:
            substituted_var = f"{essential}_substituted"
            lines.append(f"        {substituted_var} = apply_substitution(self.{essential}, floatings)")
            lines.append(f"        if {repr(essential)} not in essentials:")
            lines.append(f"            raise Exception({repr(essential + ' must be in essentials')})")
            lines.append(f"        if essentials[{repr(essential)}] != {substituted_var}:")
            lines.append(
                f"            raise Exception(f\"{essential} must be equal {{{substituted_var}}} but was {{essentials[{repr(essential)}]}}\")"
            )
        lines.append(f"        assertion_substituted = apply_substitution(self.assertion, floatings)")
        lines.append(f"        return assertion_substituted")
        lines.append("")

        return "\n".join(lines)

    def _render_proof_source(self, label: str) -> str:
        lines: list[str] = []
        lines.append(f"from metamath2py.classes.{label} import {label}")
        lines.append("")
        lines.append("")
        lines.append(f"class {label}_proof({label}):")
        lines.append("    def proof(self):")

        for step in self.proof_state.steps:
            comment = f"  # {step.comment}" if step.comment else ""
            lines.append(f"        {step.left} = {repr(step.right)}{comment}")

        if self.proof_state.steps:
            final_var = self.proof_state.steps[-1].left
            lines.append("")
            lines.append(f"        if {final_var} != self.assertion:")
            lines.append(
                f"            raise Exception(f\"{final_var} was equal {{{final_var}}}, but expected it to be equal to assertion: {{self.assertion}}\")"
            )
        else:
            lines.append("        # No steps provided; nothing to verify.")
        lines.append("")

        return "\n".join(lines)

    def _write_sources(self, class_source: str, proof_source: str) -> Tuple[Path, Path]:
        classes_root = Path(classes_folder_path)
        proofs_root = Path(proofs_folder_path)
        classes_root.mkdir(parents=True, exist_ok=True)
        proofs_root.mkdir(parents=True, exist_ok=True)

        class_path = classes_root / f"{self.theorem_state.label}.py"
        proof_path = proofs_root / f"{self.theorem_state.label}.py"

        if class_path.exists() or proof_path.exists():
            raise FileExistsError(f"Target files already exist for label {self.theorem_state.label}")

        class_path.write_text(class_source)
        proof_path.write_text(proof_source)
        return class_path, proof_path

    def _cleanup(self, paths: Iterable[Path]) -> None:
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                # Swallow cleanup errors; verification result already computed.
                pass

    def verify(self) -> ProofCheckResult:
        """
        Reconstruct temporary theorem/proof modules, run verification, clean up, and
        return the ProofCheckResult.
        """

        class_source, proof_source = self.recover_theorem_data()
        written_paths: Tuple[Path, Path] | tuple[()] = tuple()

        try:
            written_paths = self._write_sources(class_source, proof_source)
            result = verify_proof(self.theorem_state.label)
        finally:
            if written_paths:
                self._cleanup(written_paths)

        return result
