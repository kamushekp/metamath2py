import os
from pathlib import Path

from tqdm import tqdm

from paths import proofs_folder_path, PathsEnum

from verification import iter_statement_names, verify_proof


if __name__ == '__main__':
    if not os.path.isdir(proofs_folder_path):
        raise SystemExit(f"Proofs folder '{proofs_folder_path}' does not exist")

    failures = []
    for statement_name in tqdm(iter_statement_names(root_path=proofs_folder_path)):
        package = f"{PathsEnum.metamath2py_folder_name}.{PathsEnum.proofs_folder_name}"
        result = verify_proof(statement_name=statement_name, package=package)
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
