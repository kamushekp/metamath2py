import pandas as pd

from mmverify.paths import class_variables_path


def replace_class_variables(text: str):
    path = class_variables_path
    replaces = pd.read_csv(path, sep=' ')

    for _, row in replaces.iterrows():
        text = text.replace(row['token'], row['replacement'])

    return text

def reverse_replace_class_variables(text: str):
    path = class_variables_path
    replaces = pd.read_csv(path, sep=' ')

    for _, row in replaces.iterrows():
        text = text.replace(row['replacement'], row['token'])

    return text
