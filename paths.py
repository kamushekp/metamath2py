import os.path
from enum import StrEnum

from dotenv import load_dotenv

from from_root import from_root, from_here
load_dotenv(from_root(".env"))

PROJECT_PATH = from_here()

class_variables_path = os.path.join(PROJECT_PATH, 'code_builders','class_variables.csv')
pythonic_names_map_path = os.path.join(PROJECT_PATH, 'code_builders', 'pythonic_names_map.csv')


class PathsEnum(StrEnum):
    metamath2py_folder_name = 'metamath2py'
    proofs_folder_name = 'proofs'
    classes_folder_name = 'classes'

mmverify_output_folder = os.path.join(PROJECT_PATH, PathsEnum.metamath2py_folder_name)
proofs_folder_path = os.path.join(mmverify_output_folder, PathsEnum.proofs_folder_name)
classes_folder_path = os.path.join(mmverify_output_folder, PathsEnum.classes_folder_name)

metamath_path = 'PATH TO METAMATH SET.MM FILE.'