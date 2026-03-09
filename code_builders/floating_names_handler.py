from __future__ import annotations

import keyword
import os
import re
from typing import Dict

from paths import floating_names_map_path

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NON_IDENTIFIER_CHARS = re.compile(r"[^A-Za-z0-9_]")
_ESCAPE_PREFIX = "__mm__"


def _ensure_mapping_file_exists(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass


def _encode_non_identifier_char(match: re.Match[str]) -> str:
    char = match.group(0)
    codepoint = ord(char)
    return f"{_ESCAPE_PREFIX}{codepoint:04X}"


class FloatingNamesHandler:
    """Convert Metamath floating variable names into valid Python identifiers."""

    def __init__(self) -> None:
        _ensure_mapping_file_exists(floating_names_map_path)
        self._map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}
        self._load_existing_mappings()

    def _load_existing_mappings(self) -> None:
        with open(floating_names_map_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                original, sanitized = line.split(" ", maxsplit=1)
                self._map[original] = sanitized
                self._reverse_map[sanitized] = original

    def _persist_mapping(self, original: str, sanitized: str) -> None:
        with open(floating_names_map_path, "a", encoding="utf-8") as file:
            file.write(f"{original} {sanitized}\n")

    def _basic_sanitize(self, name: str) -> str:
        sanitized = _NON_IDENTIFIER_CHARS.sub(_encode_non_identifier_char, name)
        if not sanitized:
            sanitized = f"{_ESCAPE_PREFIX}0000"
        if sanitized[0].isdigit():
            sanitized = f"{_ESCAPE_PREFIX}{sanitized}"
        if keyword.iskeyword(sanitized):
            sanitized = f"{sanitized}_"
        return sanitized

    def sanitize(self, name: str) -> str:
        """Return a stable Python identifier for ``name``."""

        if name in self._map:
            return self._map[name]

        candidate = self._basic_sanitize(name)
        if not _VALID_IDENTIFIER.match(candidate):
            candidate = f"{_ESCAPE_PREFIX}{candidate}"

        if candidate == name:
            self._map[name] = candidate
            self._reverse_map.setdefault(candidate, name)
            return candidate

        suffix = 1
        unique_candidate = candidate
        while unique_candidate in self._reverse_map and self._reverse_map[unique_candidate] != name:
            suffix += 1
            unique_candidate = f"{candidate}_{suffix}"

        self._map[name] = unique_candidate
        self._reverse_map[unique_candidate] = name
        self._persist_mapping(name, unique_candidate)
        return unique_candidate

    def desanitize(self, sanitized: str) -> str:
        """Return the original Metamath name if it was previously sanitised."""

        return self._reverse_map.get(sanitized, sanitized)

    def list_sanitized_names(self) -> Dict[str, str]:
        return dict(self._map)


floating_names_handler = FloatingNamesHandler()

__all__ = ["FloatingNamesHandler", "floating_names_handler"]
