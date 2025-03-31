from dotenv import load_dotenv

from from_root import from_root
load_dotenv(from_root(".env"))

class_variables_path = from_root('mmverify','code_builders','class_variables.csv')
pythonic_names_map_path = from_root('mmverify','code_builders', 'pythonic_names_map.csv')

mmverify_output_folder = from_root('metamath2py')
proofs_folder_path = from_root('metamath2py', "proofs")
classes_folder_path = from_root('metamath2py', "classes")
comments_folder_path = from_root('metamath2py', "comments")

comments_path = from_root( 'service', 'comments.json')

metamath_path = 'PATH TO METAMATH SET.MM FILE.'