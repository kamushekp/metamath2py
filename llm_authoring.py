"""High-level helpers for LLMs to author metamath2py classes and proofs.

The module provides two user-friendly builders:

``TheoremClassAuthor``
    Guides the creation of class-definition files ("statements") by collecting
    floating/essential hypotheses and the assertion.  The builder handles code
    generation, syntax validation, and file-system bookkeeping so that an LLM can
    focus on the mathematical content.

``ProofAuthor``
    Assists with crafting proof files by accumulating imports and proof steps in
    a structured way.  The author exposes helpers for common actions (assigning
    string constants, calling previously defined classes) and integrates with the
    verification helpers to provide actionable feedback when a proof fails.

Both builders return structured results containing validation issues with line
numbers and snippets whenever Python raises a syntax error.  This feedback is
intended for iterative refinement loops where an LLM inspects the reported
problems and attempts another revision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from metamath2py.verification import ProofCheckResult, verify_proof

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CLASSES_DIR = PACKAGE_ROOT / "classes"
DEFAULT_PROOFS_DIR = PACKAGE_ROOT / "proofs"
DEFAULT_PROOFS_PACKAGE = "metamath2py.proofs"


@dataclass
class ValidationIssue:
    """Represents a user-facing validation issue."""

    stage: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    snippet: Optional[str] = None


@dataclass
class WriteResult:
    """Outcome of writing a generated file to disk."""

    success: bool
    path: Optional[Path]
    issues: List[ValidationIssue] = field(default_factory=list)


def _ensure_package_layout(target_dir: Path, *, ensure_apply_substitution: bool = False) -> None:
    """Create the package directory if needed and drop a blank ``__init__`` file."""

    target_dir.mkdir(parents=True, exist_ok=True)
    init_file = target_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")

    if ensure_apply_substitution:
        bridge = target_dir / "apply_substitution_for_generated_files.py"
        if not bridge.exists():
            bridge.write_text(
                """from __future__ import annotations\n\n"""
                "from metamath2py.apply_substitution_for_generated_files import apply_substitution\n\n"
                "__all__ = [\"apply_substitution\"]\n",
                encoding="utf-8",
            )


def _validate_python(code: str, *, filename: str) -> List[ValidationIssue]:
    try:
        compile(code, filename, "exec")
    except SyntaxError as exc:
        return [
            ValidationIssue(
                stage="syntax",
                message=exc.msg,
                line=exc.lineno,
                column=exc.offset,
                snippet=(exc.text.strip() if exc.text else None),
            )
        ]
    return []


class TheoremClassAuthor:
    """Incrementally build a class-definition file."""

    def __init__(
        self,
        name: str,
        *,
        target_dir: Path = DEFAULT_CLASSES_DIR,
    ) -> None:
        self.name = name
        self.target_dir = target_dir
        self.comment: str = ""
        self.floatings: List[str] = []
        self.essentials: List[str] = []
        self.assertion: Optional[str] = None

    # ------------------------------------------------------------------ helpers
    def set_comment(self, comment: str) -> None:
        self.comment = comment or ""

    def add_floating(self, token: str) -> None:
        if token in self.floatings:
            raise ValueError(f"Floating variable '{token}' already registered")
        self.floatings.append(token)

    def add_essential(self, statement: str) -> None:
        if not statement:
            raise ValueError("Essential statement must be non-empty")
        self.essentials.append(statement)

    def set_assertion(self, assertion: str) -> None:
        if not assertion:
            raise ValueError("Assertion must be non-empty")
        self.assertion = assertion

    # ----------------------------------------------------------------- rendering
    def _build_floatings_block(self) -> str:
        if not self.floatings:
            return "    pass"
        return "\n".join(f"    {name}: str" for name in self.floatings)

    def _build_essentials_block(self) -> str:
        if not self.essentials:
            return "    pass"
        return "\n".join(f"    essential_{i}: str" for i in range(1, len(self.essentials) + 1))

    def _build_essentials_assignment(self) -> str:
        lines: List[str] = []
        for i, content in enumerate(self.essentials, start=1):
            lines.append(f"        self.essential_{i} = r\"\"\"{content}\"\"\"")
        if lines:
            lines.append("")
        return "\n".join(lines)

    def _build_essential_substitutions(self) -> str:
        blocks: List[str] = []
        for i, _ in enumerate(self.essentials, start=1):
            blocks.append(
                (
                    "        essential_{idx}_substituted = apply_substitution(self.essential_{idx}, floatings)\n"
                    "        if \"essential_{idx}\" not in essentials:\n"
                    "            raise Exception(\"essential_{idx} must be in essentials\")\n"
                    "        if essentials[\"essential_{idx}\"] != essential_{idx}_substituted:\n"
                    "            raise Exception(f'essentials[\"essential_{idx}\"] must be equal {{essential_{idx}_substituted}} but was {{essentials[\"essential_{idx}\"]}}')"
                ).format(idx=i)
            )
        if blocks:
            return "\n".join(blocks) + "\n"
        return ""

    def _build_class_body(self) -> str:
        essentials_assignment = self._build_essentials_assignment()
        essential_substitutions = self._build_essential_substitutions()
        assertion = self.assertion or ""
        return (
            f"class {self.name}:\n"
            f"    \"\"\"{self.comment}\"\"\"\n"
            "    def __init__(self):\n"
            f"{essentials_assignment}        self.assertion = r\"\"\"{assertion}\"\"\"\n\n"
            f"    def call(self, floatings: {self.name}_FloatingArgs, essentials: {self.name}_EssentialArgs):\n"
            f"{essential_substitutions}        assertion_substituted = apply_substitution(self.assertion, floatings)\n"
            "        return assertion_substituted\n"
        )

    def render(self) -> str:
        if self.assertion is None:
            raise ValueError("Assertion was not set")

        floating_block = self._build_floatings_block()
        essential_block = self._build_essentials_block()
        class_body = self._build_class_body()

        sections = [
            "from typing import TypedDict",
            "from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution",
            "",
            f"class {self.name}_FloatingArgs(TypedDict):",
            floating_block,
            "",
            "",
            f"class {self.name}_EssentialArgs(TypedDict):",
            essential_block,
            "",
            "",
            class_body,
            "",
        ]
        return "\n".join(sections)

    # -------------------------------------------------------------------- saving
    def save(self, *, filename: Optional[str] = None, overwrite: bool = True) -> WriteResult:
        filename = filename or f"{self.name}.py"
        _ensure_package_layout(self.target_dir, ensure_apply_substitution=True)
        path = self.target_dir / filename

        code = self.render()
        issues = _validate_python(code, filename=str(path))
        if issues:
            return WriteResult(success=False, path=None, issues=issues)

        if path.exists() and not overwrite:
            return WriteResult(
                success=False,
                path=None,
                issues=[ValidationIssue(stage="io", message=f"File {path} already exists")],
            )

        path.write_text(code, encoding="utf-8")
        return WriteResult(success=True, path=path)


class ProofAuthor:
    """Helper class to construct a proof file."""

    def __init__(
        self,
        name: str,
        *,
        target_dir: Path = DEFAULT_PROOFS_DIR,
        package: str = DEFAULT_PROOFS_PACKAGE,
    ) -> None:
        self.name = name
        self.target_dir = target_dir
        self.package = package
        self.imports: List[str] = []
        self.body_lines: List[str] = []
        self.last_step: Optional[str] = None

        # Always import the statement under proof.
        self.add_import(name)

    def add_import(self, statement_name: str) -> None:
        import_line = f"from metamath2py.classes.{statement_name} import {statement_name}"
        if import_line not in self.imports:
            self.imports.append(import_line)

    def add_body_line(self, line: str) -> None:
        self.body_lines.append(line)

    def add_constant(self, target: str, value: str) -> None:
        self.add_body_line(f"        {target} = \"{value}\"")

    def add_call(
        self,
        target: str,
        statement: str,
        *,
        floatings: Optional[Dict[str, str]] = None,
        essentials: Optional[Dict[str, str]] = None,
    ) -> None:
        self.add_import(statement)
        float_str = self._format_dict(floatings)
        ess_str = self._format_dict(essentials)
        self.add_body_line(
            f"        {target} = {statement}().call({float_str}, {ess_str})"
        )

    @staticmethod
    def _format_dict(values: Optional[Dict[str, str]]) -> str:
        if not values:
            return "{}"
        parts = [f'"{key}": {value}' for key, value in values.items()]
        return "{" + ", ".join(parts) + "}"

    def set_last_step(self, variable_name: str) -> None:
        self.last_step = variable_name

    def render(self) -> str:
        if self.last_step is None:
            raise ValueError("The proof must define the last step before rendering")

        imports_block = "\n".join(self.imports)
        body = "\n".join(self.body_lines)
        assertion_check = (
            f"        if {self.last_step} != self.assertion:\n"
            f"            raise Exception(f\"{self.last_step} was equal {{{self.last_step}}}, but expected it to be equal to assertion: {{self.assertion}}\")"
        )
        sections = [
            imports_block,
            "",
            f"class {self.name}_proof({self.name}):",
            "    def proof(self):",
            body,
            assertion_check,
            "",
        ]
        return "\n".join(sections)

    def save(self, *, filename: Optional[str] = None, overwrite: bool = True) -> WriteResult:
        filename = filename or f"{self.name}.py"
        _ensure_package_layout(self.target_dir)
        path = self.target_dir / filename

        code = self.render()
        issues = _validate_python(code, filename=str(path))
        if issues:
            return WriteResult(success=False, path=None, issues=issues)

        if path.exists() and not overwrite:
            return WriteResult(
                success=False,
                path=None,
                issues=[ValidationIssue(stage="io", message=f"File {path} already exists")],
            )

        path.write_text(code, encoding="utf-8")
        return WriteResult(success=True, path=path)

    # --------------------------------------------------------------- verification
    def verify(self) -> ProofCheckResult:
        """Import the saved proof module and execute it."""

        relative_name = Path(f"{self.name}").as_posix().replace("/", ".")
        return verify_proof(relative_name, package=self.package)


class AuthoringWorkspace:
    """Convenience wrapper bundling class and proof builders together."""

    def __init__(
        self,
        *,
        classes_dir: Path = DEFAULT_CLASSES_DIR,
        proofs_dir: Path = DEFAULT_PROOFS_DIR,
        proofs_package: str = DEFAULT_PROOFS_PACKAGE,
    ) -> None:
        self.classes_dir = classes_dir
        self.proofs_dir = proofs_dir
        self.proofs_package = proofs_package

    def new_class(self, name: str) -> TheoremClassAuthor:
        return TheoremClassAuthor(name, target_dir=self.classes_dir)

    def new_proof(self, name: str) -> ProofAuthor:
        return ProofAuthor(name, target_dir=self.proofs_dir, package=self.proofs_package)


__all__ = [
    "AuthoringWorkspace",
    "ProofAuthor",
    "ProofCheckResult",
    "TheoremClassAuthor",
    "ValidationIssue",
    "WriteResult",
]
