from typing import Type, Dict, List


class DictWithCollisions:
    def __init__(self, key_type: Type, values_type: Type):
        self._inner_dict: Dict[key_type, List[values_type]] = {}

    def add(self, key, value):
        if key not in self._inner_dict:
            self._inner_dict[key] = [value]
        else:
            self._inner_dict[key].append(value)

    def iter_values(self):
        for l in self._inner_dict.values():
            for v in l:
                yield v