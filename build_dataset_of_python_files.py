import json
import os
import shutil

from paths import classes_folder_path, proofs_folder_path, mmverify_output_folder


def write_to_files(name, executable_class, executable_proof):
    class_path = os.path.join(classes_folder_path, f'{name}.py')
    proof_path = os.path.join(proofs_folder_path, f'{name}.py')
    mode = 'w+'
    with open(class_path, mode) as f:
        f.write(executable_class)
    with open(proof_path, mode) as f:
        f.write(executable_proof)


if __name__ == '__main__':
    if not os.path.exists(mmverify_output_folder):
        os.mkdir(mmverify_output_folder)

    if not os.path.exists(classes_folder_path):
        os.mkdir(classes_folder_path)
    if not os.path.exists(proofs_folder_path):
        os.mkdir(proofs_folder_path)


    shutil.copy2('apply_substitution_for_generated_files.py', classes_folder_path)
    shutil.copy2('__init__.py', classes_folder_path)
    shutil.copy2('__init__.py', proofs_folder_path)

    with open('metamath2py.jsonl', "r") as f:
        for line in f:
            model = json.loads(line.rstrip())
            executable_class = model['executable_class']
            executable_proof = model['executable_proof']
            name = model['name']
            write_to_files(name, executable_class, executable_proof)