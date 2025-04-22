import random
import string

from paths import pythonic_names_map_path


def generate_unique_name(length, exclusions):
    while True:
        name = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
               ''.join(random.choices(string.ascii_uppercase + string.digits[1:], k=length - 1))
        if name not in exclusions:
            return name


def read_file_to_dict(file_path):
    result_dict = {}

    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split()
            result_dict[key] = value

    return result_dict

def read_file_to_dict_reverse(file_path):
    result_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split()
            result_dict[value] = key

    return result_dict


class PythonicNamesHandler:
    def __init__(self):
        self.map_path = pythonic_names_map_path

        self.maps = read_file_to_dict(self.map_path)
        self.reverse_map = read_file_to_dict_reverse(self.map_path)

    def map_name(self, name: str):
        if name in self.maps:
            return self.maps[name]
        pythonic_name = generate_unique_name(5, self.maps)
        with open(self.map_path, 'a') as f:
            f.write(f'{name} {pythonic_name}\n')

        self.maps[name] = pythonic_name

        return pythonic_name

    def reverse_map_name(self, name: str):
        if name in self.reverse_map:
            return self.reverse_map[name]
        return None

    def list_encoded_names(self):
        return self.maps.values()
