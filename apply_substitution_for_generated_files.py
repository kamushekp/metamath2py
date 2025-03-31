def apply_substitution(statement: str, substitution: dict[str, str]) -> str:
    result = []
    for tok in statement.split(sep=' '):
        if tok in substitution:
            parts = substitution[tok].split(' ')
            parts = parts[1:]  # Usually there is a specifier: wff, class and maybe setvar before the token to be replaced. We remove it because it is not needed.
            with_no_specifier = ' '.join(parts)
            result.append(with_no_specifier)
        else:
            result.append(tok)
    return ' '.join(result)