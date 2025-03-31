from typing import Tuple, Optional

from mmverify.models.errors import MMError


class Toks:
    """Class of sets of tokens from which functions read as in an input
    stream.
    """

    def __init__(self, filepath: str) -> None:
        """Инициализируем считывание из одного файла."""
        self.tokbuf: list[str] = []
        with open(filepath, mode='r', encoding='ascii') as file:
            self.lines = [l for l in file.read().splitlines() if l]
        self.current_line = 0

    def _read(self) -> str:
        """Считывает следующий токен из буфера или загружает следующую строку, если буфер пуст."""
        if not self.tokbuf:
            if self.current_line < len(self.lines):
                line = self.lines[self.current_line]
                self.current_line += 1
                self.tokbuf = line.split()
                self.tokbuf.reverse()
            else:
                return None  # Конец файла
        return self.tokbuf.pop()

    def readc(self) -> Tuple[Optional[str], str]:
        """Читает следующий токен, пропуская комментарии."""
        tok = self._read()
        comment = []
        while tok == '$(':  # Начало комментария
            while tok and tok != '$)':  # Пропускаем содержимое комментария
                tok = self._read()
                comment.append(tok)
            if not tok:
                raise MMError("Unclosed comment at end of file.")
            tok = self._read()  # Читаем токен после закрытия комментария
            if tok == '$(': # если за комментарием идет еще комментарий, пропускаем его
                comment = []
        comment = ' '.join(comment[:-1]) if len(comment) > 0 else None
        return comment, tok

