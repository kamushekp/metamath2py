import os

from tqdm import tqdm

from paths import proofs_folder_path


def enumerate_proofs_names():
    for dirpath, dnames, fnames in os.walk(proofs_folder_path):
        for f in tqdm(fnames):
            if f[-3:] != '.py' and f != '__init__.py':
                continue

            statement_name = f[:-3]
            yield statement_name


if __name__ == '__main__':
    for statement_name in enumerate_proofs_names():

        code = f"""
from metamath2py.proofs.{statement_name} import {statement_name}_proof
{statement_name}_proof().proof()
        """

        try:
            exec(code)
        except Exception as e:
            print(str(e))