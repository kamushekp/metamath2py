# Repository Guidelines

## Project Structure & Module Organization
The core translator logic lives in `metamath2py/`, with reusable proof builders in `code_builders/` and domain objects in `classes/`. Dataset helpers (JSONL builders, substitution tools) sit at repository root for clarity, while reusable resources such as the Metamath database snapshot reside in `database/`. Generated artifacts and diagnostics are written to `out/`, and ready-to-run example proofs are under `examples/`. Keep large datasets and checkpoints out of version control; stage only scripts or configs needed to reproduce them.

## Build, Test, and Development Commands
- `python build_jsonl_dataset.py --input path/to/set_normal.mm` generates the intermediate JSON Lines dataset from an uncompressed Metamath source.
- `python build_dataset_of_python_files.py --jsonl out/dataset.jsonl --dest out/python_dataset` emits executable theorem modules.
- `python verify_metamath2py_files.py --root out/python_dataset` validates every generated proof module and highlights failures.
- `python verification.py` exposes structured verification helpers; import `verification.verify_proof` inside notebooks or tooling for targeted checks.
Activate the project virtualenv (`source venv/bin/activate`) before running scripts so dependencies resolve consistently.

## Coding Style & Naming Conventions
Use Python 3.10+ and follow PEP 8: four-space indentation, snake_case for functions/modules, and PascalCase for classes (see `verification.py` for reference). Match existing module naming: generated proofs end with `_proof.py`, and factory functions mirror the file stem (e.g., `A1WQA_proof`). Keep imports explicit; avoid wildcard imports to preserve deterministic verification. Run `ruff check .` if you have Ruff installed—fix any flagged issues before opening a PR.

## Testing Guidelines
Primary verification happens through `verify_metamath2py_files.py`; ensure new statements import cleanly and execute their `proof()` method without raising exceptions. For incremental work, call `verification.verify_proof("statement", package="out.python_dataset")` to surface stage-specific errors. There is no enforced coverage threshold yet, but add regression cases in `examples/` when fixing bugs so future dataset builds remain reproducible.

## Commit & Pull Request Guidelines
Follow the existing history: short, imperative subjects (`fix package discovery`, `add LLM authoring helpers`) and include issue or PR references when relevant (`#4`). Squash incidental WIP commits locally. Pull requests should describe the motivation, outline verification results (commands run and outcomes), attach or link datasets if they exceed `out/`, and note any follow-up tasks. Include screenshots or traceback snippets when the change touches tooling UX to accelerate review.
