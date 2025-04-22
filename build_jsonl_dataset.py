import json
import sys

from metamath_adapter import MetamathHandler
from mm import MM
from models.toks import Toks
from paths import metamath_path

print("\n".join(sys.path))
if __name__ == '__main__':

    handler = MetamathHandler()
    mm = MM()
    results = []
    metamath_path = r'C:\Users\kamus\PycharmProjects\metamath\set_normal.mm' #change it for your path!
    toks = Toks(metamath_path)

    with open('metamath2py.jsonl', "a+") as f:
        for statement_info in mm.read(toks):
            #a = 5
            original_name = statement_info['original_name']
            lemmon_notation = handler.read_proof(original_name)
            statement_info['lemmon_notation'] = lemmon_notation
            row = json.dumps(statement_info)
            f.write(row + '\n')