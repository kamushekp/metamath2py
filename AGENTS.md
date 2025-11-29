# Repository Guidelines

## Project Structure & Module Organization
- Core translator logic: `metamath2py/`; reusable proof builders: `code_builders/`; domain objects: `classes/`.
- Dataset helpers (JSONL builders, substitution tools) sit at repo root for clarity; Metamath database snapshots live in `database/`.
- Generated artifacts and diagnostics go to `out/`; ready-to-run example proofs are under `examples/`; tests live in `tests/`.
- Keep large datasets and checkpoints out of version control; commit only the scripts/configs to reproduce them.

## Build, Test, and Development Commands
- Create JSONL dataset from an uncompressed Metamath source:  
  `python build_jsonl_dataset.py --input path/to/set_normal.mm`
- Emit executable theorem modules from the JSONL dataset:  
  `python build_dataset_of_python_files.py --jsonl out/dataset.jsonl --dest out/python_dataset`
- Validate generated proof modules:  
  `python verify_metamath2py_files.py --root out/python_dataset`
- Ad-hoc verification helpers inside code/notebooks:  
  `python - <<'PY'\nfrom verification import verify_proof\nverify_proof(\"statement_name\")\nPY`
- Before running scripts, activate the virtualenv: `source venv/bin/activate`.

## Coding Style & Naming Conventions
- Python 3.10+; follow PEP 8 with 4-space indentation and snake_case for functions/modules, PascalCase for classes.
- Generated proof modules end with `_proof.py`; factory functions mirror the file stem (e.g., `A1WQA_proof`).
- Keep imports explicit; avoid `from x import *` to preserve deterministic verification.
- If available, run `ruff check .` and address reported issues.
- Prefer method/function signatures, call sites, and object initializations on a single line; avoid wrapping arguments and avoid `*args`/`**kwargs` unless absolutely unavoidable.
- Do not edit or populate `__init__.py` files unless explicitly requested.

## Testing Guidelines
- Primary check is `verify_metamath2py_files.py` on generated modules; ensure `proof()` executes without exceptions.
- For incremental work, call `verification.verify_proof("statement")` to surface stage-specific errors.
- Add regression examples in `examples/` when fixing bugs to keep dataset builds reproducible.

## Commit & Pull Request Guidelines
- Use short, imperative commit subjects (e.g., `fix package discovery`); include issue/PR references when relevant (e.g., `#4`).
- Squash incidental WIP commits locally.
- PRs should explain motivation, list verification results (commands and outcomes), and note follow-ups; attach or link datasets if they exceed `out/`.
- Include screenshots or traceback snippets when tooling UX is affected to speed up review.
