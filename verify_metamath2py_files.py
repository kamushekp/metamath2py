import os
from pathlib import Path

try:  # pragma: no cover - tqdm is optional in lightweight environments
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, *args, **kwargs):  # type: ignore[misc]
        return iterable

try:
    from paths import proofs_folder_path  # type: ignore
except ModuleNotFoundError:
    proofs_folder_path = Path(__file__).resolve().parent / "proofs"

try:
    from metamath2py.verification import iter_statement_names, verify_proof
except ModuleNotFoundError:
    from verification import iter_statement_names, verify_proof  # type: ignore


if __name__ == '__main__':
    if not os.path.isdir(proofs_folder_path):
        raise SystemExit(f"Proofs folder '{proofs_folder_path}' does not exist")

    failures = []
    for statement_name in tqdm(list(iter_statement_names(str(proofs_folder_path)))):
        result = verify_proof(statement_name)
        if not result.success:
            failures.append(result)
            print(f"\n[FAIL] {statement_name} ({result.stage})")
            if result.error_message:
                print(result.error_message)
            if result.traceback:
                print(result.traceback)

    if not failures:
        print("All proofs succeeded")
    else:
        print(f"Total failing proofs: {len(failures)}")
