import json
import sys

from mmverify.mm import MM
from mmverify.models.toks import Toks
from mmverify.paths import metamath_path
from obsolete.metamath_program_adapter.read_proofs import MetamathHandler

print("\n".join(sys.path))
if __name__ == '__main__':

    handler = MetamathHandler()
    mm = MM()
    results = []
    toks = Toks(metamath_path)

    with open('metamath2py.json', "a+") as f:
        for statement_info in mm.read(toks):
            original_name = statement_info['original_name']
            lemmon_notation = handler.read_proof(original_name)
            statement_info['lemmon_notation'] = lemmon_notation
            row = json.dumps(statement_info)
            f.write(row + '\n')