import os.path

from dotenv import load_dotenv

from from_root import from_root, from_here
load_dotenv(from_root(".env"))

PROJECT_PATH = from_here()

class_variables_path = os.path.join(PROJECT_PATH, 'code_builders','class_variables.csv')
pythonic_names_map_path = os.path.join(PROJECT_PATH, 'code_builders', 'pythonic_names_map.csv')

mmverify_output_folder = os.path.join(PROJECT_PATH, 'metamath2py')
proofs_folder_path = os.path.join(PROJECT_PATH, 'metamath2py', "proofs")
classes_folder_path = os.path.join(PROJECT_PATH, 'metamath2py', "classes")
comments_folder_path = os.path.join(PROJECT_PATH, 'metamath2py', "comments")

metamath_path = 'PATH TO METAMATH SET.MM FILE.'