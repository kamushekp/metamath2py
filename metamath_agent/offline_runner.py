from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import argparse
from collections import Counter
from typing import Iterable

from code_builders.class_builder import ClassBuilder
from code_builders.pythonic_names_handler import PythonicNamesHandler
from code_builders.verifier import verify
from database.opensearch_wrapper import TheoremSearchClient
from mm import MM
from models.frame import Frame
from models.mm_models import Const, FullStatement, Label, Statement, StatementType, Symbol, Var
from models.toks import Toks


@dataclass(frozen=True)
class GeneratedTheorem:
    name: str
    class_path: Path
    proof_path: Path


_NAMES = PythonicNamesHandler()


def _next_name(base_name: str) -> str:
    return f"{base_name}_X" if base_name.endswith("_ALT") else f"{base_name}_ALT"


def _resolve_metamath_binary() -> Path:
    candidates = (
        Path("metamath_program/metamath/metamath"),
        Path("metamath_program/metamath/metamath.exe"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError("Metamath binary not found in metamath_program/metamath")


def _resolve_metamath_db() -> Path:
    candidates = (
        Path("metamath_program/metamath/set_normal.mm"),
        Path("metamath_program/metamath/set.mm"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Neither set_normal.mm nor set.mm was found")


def _run_metamath_commands(commands: list[str], *, workdir: Path) -> str:
    metamath_binary = _resolve_metamath_binary()
    payload = "\n".join(commands) + "\n"
    completed = subprocess.run(
        [str(metamath_binary)],
        input=payload,
        text=True,
        capture_output=True,
        cwd=str(workdir),
        check=True,
    )
    return completed.stdout


def _extract_normal_proof_tokens(metamath_output: str, *, theorem_label: str) -> list[str]:
    lines = metamath_output.splitlines()
    collecting = False
    proof_tokens: list[str] = []
    expected_header = f'Proof of "{theorem_label}":'

    for raw_line in lines:
        line = raw_line.strip()
        if line == expected_header:
            collecting = False
            continue
        if "Clip out the proof below this line" in line:
            collecting = True
            continue
        if "ends above this line" in line:
            break
        if not collecting:
            continue
        proof_tokens.extend(line.split())

    if not proof_tokens:
        raise ValueError(f"Could not extract proof tokens for theorem {theorem_label}")
    if proof_tokens[-1] == "$.":
        proof_tokens.pop()
    return proof_tokens


def _normalized_proof_tokens(*, theorem_label: str, metamath_db: Path) -> list[str]:
    db_name = metamath_db.name
    output = _run_metamath_commands(
        [
            "SET SCROLL CONTINUOUS",
            f'READ "{db_name}"',
            f"SAVE PROOF {theorem_label} / NORMAL",
            f"SHOW PROOF {theorem_label} / NORMAL",
            "EXIT",
            "Y",
        ],
        workdir=metamath_db.parent,
    )
    return _extract_normal_proof_tokens(output, theorem_label=theorem_label)


def _recover_by_original_label(*, original_label: str, normalized_tokens: list[str]) -> dict[str, str]:
    mm = MM()
    toks = Toks(str(_resolve_metamath_db()))

    current_frame = Frame()
    mm.frame_stack.push(current_frame)

    label: Label | None = None
    prev_label: Label | None = None

    comment, tok = toks.readc()
    mm.append_comment_if_exists(comment)

    while tok:
        statement_type = StatementType.try_cast(tok)

        if statement_type == StatementType.constant:
            statement = mm.read_non_p_stmt(statement_type, toks)
            mm.add_constants(statement)
        elif statement_type == StatementType.variable:
            statement = mm.read_non_p_stmt(statement_type, toks)
            mm.add_variables(current_frame, statement)
        elif statement_type == StatementType.floating:
            statement = mm.read_non_p_stmt(statement_type, toks)
            if not label:
                raise ValueError("Encountered $f without active label")
            if len(statement.statement_content) != 2:
                raise ValueError("Floating statement must contain exactly 2 symbols")
            typecode = Const(statement.statement_content[0].content)
            variable = Var(statement.statement_content[1].content)
            mm.add_floating(current_frame, typecode=typecode, var=variable, label=label)
            mm.labels[label] = FullStatement(label, StatementType.floating, statement)
            label = None
        elif statement_type == StatementType.essential:
            if not label:
                raise ValueError("Encountered $e without active label")
            statement = mm.read_non_p_stmt(statement_type, toks)
            current_frame.add_essential(statement, label)
            mm.labels[label] = FullStatement(label, StatementType.essential, statement)
            label = None
        elif statement_type == StatementType.assertion:
            if not label:
                raise ValueError("Encountered $a without active label")
            statement = mm.read_non_p_stmt(statement_type, toks)
            assertion = mm.frame_stack.make_assertion(statement)
            mm.labels[label] = FullStatement(label, StatementType.assertion, assertion)
            label = None
            mm.comments = []
        elif statement_type == StatementType.provable:
            if not label:
                raise ValueError("Encountered $p without active label")

            statement, _proof = mm.read_p_stmt(toks)
            assertion = mm.frame_stack.make_assertion(statement)
            comment_text = mm.comments[-1] if mm.comments else ""
            mm.comments = []

            if label.name == original_label:
                builder = ClassBuilder()
                builder.set_comment(comment_text)
                builder.set_statement_name(label.name)
                builder.set_assertion(assertion)
                normalized_statement = Statement(statement_content=[Symbol(content=t) for t in normalized_tokens])
                verify(
                    frame_stack=mm.frame_stack,
                    labels=mm.labels,
                    target_statement=assertion.statement,
                    proof=normalized_statement,
                    builder=builder,
                )
                mm.labels[label] = FullStatement(label, StatementType.provable, assertion)
                return builder.build()

            mm.labels[label] = FullStatement(label, StatementType.provable, assertion)
            label = None
        elif statement_type == StatementType.definition:
            statement = mm.read_non_p_stmt(statement_type, toks)
            current_frame.add_definitions(statement)
        elif tok == "${":
            current_frame = Frame()
            mm.frame_stack.push(current_frame)
            prev_label = label
            label = None
        elif tok == "$}":
            mm.frame_stack.pop()
            current_frame = mm.frame_stack[-1]
            label = prev_label
        elif tok == "$)":
            raise ValueError("Unexpected closing comment token")
        elif tok[0] != "$":
            candidate = Label(tok)
            if candidate in mm.labels:
                raise ValueError(f"Label already defined: {tok}")
            label = candidate
        else:
            raise ValueError(f"Unknown token while parsing Metamath source: {tok}")

        comment, tok = toks.readc()
        mm.append_comment_if_exists(comment)

    raise ValueError(f"Could not reconstruct theorem by original label: {original_label}")


def _recover_artifacts_via_metamath(*, base_name: str) -> dict[str, str]:
    original_label = _NAMES.reverse_map_name(base_name) or base_name
    normalized_tokens = _normalized_proof_tokens(
        theorem_label=original_label,
        metamath_db=_resolve_metamath_db(),
    )
    return _recover_by_original_label(original_label=original_label, normalized_tokens=normalized_tokens)


def _extract_theorem_name_from_path(path: str) -> str | None:
    path_obj = Path(path)
    if path_obj.suffix != ".py":
        return None
    if len(path_obj.parts) < 2:
        return None
    if path_obj.parts[-2] not in {"classes", "proofs"}:
        return None
    return path_obj.stem


def _iter_candidate_names_from_search(
    *,
    client: TheoremSearchClient,
    queries: Iterable[str],
    top_k: int = 20,
) -> list[str]:
    score_by_name: Counter[str] = Counter()
    for query in queries:
        cleaned = query.strip()
        if not cleaned:
            continue
        results = client.search(cleaned, top_k=top_k, highlight=False)
        for rank, result in enumerate(results):
            name = _extract_theorem_name_from_path(result.path)
            if not name:
                continue
            # Combine retrieval rank and score into one robust voting metric.
            score_by_name[name] += max(1, top_k - rank) + int(max(0.0, result.score))

    return [name for name, _ in score_by_name.most_common()]


def _load_artifacts_from_index(*, client: TheoremSearchClient, theorem_name: str) -> dict[str, str] | None:
    class_source = client.get_document_text(f"classes/{theorem_name}.py")
    proof_source = client.get_document_text(f"proofs/{theorem_name}.py")

    if not class_source or not proof_source:
        # Support alternative dataset roots that may include nested folders.
        docs = client.list_documents()
        if not class_source:
            class_doc = next((d for d in docs if d.endswith(f"classes/{theorem_name}.py")), None)
            if class_doc:
                class_source = client.get_document_text(class_doc)
        if not proof_source:
            proof_doc = next((d for d in docs if d.endswith(f"proofs/{theorem_name}.py")), None)
            if proof_doc:
                proof_source = client.get_document_text(proof_doc)

    if not class_source or not proof_source:
        return None

    return {
        "name": theorem_name,
        "executable_class": class_source,
        "executable_proof": proof_source,
    }


def _recover_artifacts_via_rag(*, base_name: str, description: str) -> dict[str, str]:
    client = TheoremSearchClient(host="localhost", port=9200, index_name="metamath-rag-theorems")
    if not client.ping():
        raise RuntimeError("OpenSearch is not reachable")

    original_label = _NAMES.reverse_map_name(base_name) or ""
    description_clean = description.replace("Description:", "").strip()
    candidate_queries = [description, description_clean, base_name, original_label]

    ranked_names = _iter_candidate_names_from_search(client=client, queries=candidate_queries, top_k=20)
    # Always check explicit target name first for deterministic recovery flow.
    candidates = [base_name]
    for name in ranked_names:
        if name not in candidates:
            candidates.append(name)

    for theorem_name in candidates:
        artifacts = _load_artifacts_from_index(client=client, theorem_name=theorem_name)
        if artifacts is not None:
            return artifacts

    raise ValueError(f"RAG could not recover theorem artifacts for base name {base_name}")


def _recover_artifacts(*, base_name: str, description: str, strategy: str) -> dict[str, str]:
    if strategy not in {"auto", "rag", "metamath"}:
        raise ValueError("strategy must be one of: auto, rag, metamath")

    if strategy in {"auto", "rag"}:
        try:
            return _recover_artifacts_via_rag(base_name=base_name, description=description)
        except Exception:
            if strategy == "rag":
                raise

    return _recover_artifacts_via_metamath(base_name=base_name)


def _rewrite_name(source: str, old_name: str, new_name: str) -> str:
    return source.replace(old_name, new_name)


def recover_theorem(
    *,
    base_name: str,
    output_name: str,
    description: str = "",
    strategy: str = "auto",
    classes_dir: Path,
    proofs_dir: Path,
) -> GeneratedTheorem:
    classes_path = Path(classes_dir)
    proofs_path = Path(proofs_dir)
    classes_path.mkdir(parents=True, exist_ok=True)
    proofs_path.mkdir(parents=True, exist_ok=True)

    artifacts = _recover_artifacts(base_name=base_name, description=description, strategy=strategy)
    recovered_name = artifacts["name"]

    class_target = classes_path / f"{output_name}.py"
    proof_target = proofs_path / f"{output_name}.py"

    class_source = _rewrite_name(artifacts["executable_class"], recovered_name, output_name)
    proof_source = _rewrite_name(artifacts["executable_proof"], recovered_name, output_name)

    class_target.write_text(class_source, encoding="utf-8")
    proof_target.write_text(proof_source, encoding="utf-8")

    return GeneratedTheorem(name=output_name, class_path=class_target, proof_path=proof_target)


def generate_from_description(
    *,
    base_name: str,
    description: str,
    classes_dir: Path,
    proofs_dir: Path,
    proofs_package: str | None = None,
) -> GeneratedTheorem:
    """
    Recover a theorem from Metamath source and emit generated Python artifacts.

    The reconstruction path is deterministic and does not depend on an online
    LLM or OpenSearch service.
    """

    _ = proofs_package
    new_name = _next_name(base_name)
    return recover_theorem(
        base_name=base_name,
        output_name=new_name,
        description=description,
        strategy="auto",
        classes_dir=classes_dir,
        proofs_dir=proofs_dir,
    )


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline theorem recovery from Metamath source")
    parser.add_argument("--base-name", required=True, help="Existing mapped theorem id, e.g. A0K0")
    parser.add_argument(
        "--output-name",
        default=None,
        help="Output theorem name; defaults to base name (restoration in-place).",
    )
    parser.add_argument(
        "--classes-dir",
        default="metamath2py/classes",
        help="Directory to write theorem class module into.",
    )
    parser.add_argument(
        "--proofs-dir",
        default="metamath2py/proofs",
        help="Directory to write theorem proof module into.",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Natural-language description used by RAG retrieval.",
    )
    parser.add_argument(
        "--strategy",
        default="auto",
        choices=("auto", "rag", "metamath"),
        help="Recovery backend: RAG via OpenSearch, Metamath parsing, or auto fallback.",
    )
    parser.add_argument("--verify", action="store_true", help="Run verification.verify_proof(output_name) after writing files.")
    return parser


def _main() -> int:
    parser = _build_cli_parser()
    args = parser.parse_args()

    output_name = args.output_name or args.base_name
    generated = recover_theorem(
        base_name=args.base_name,
        output_name=output_name,
        description=args.description,
        strategy=args.strategy,
        classes_dir=Path(args.classes_dir),
        proofs_dir=Path(args.proofs_dir),
    )

    print(f"Recovered theorem: {generated.name}")
    print(f"Class file: {generated.class_path}")
    print(f"Proof file: {generated.proof_path}")

    if args.verify:
        from verification import verify_proof

        result = verify_proof(generated.name)
        print(f"Verification: success={result.success}, stage={result.stage}")
        if not result.success:
            print(result.error_message or "")
            if result.traceback:
                print(result.traceback)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
