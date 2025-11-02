from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    role: str
    content: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # These fields are populated by the search tree as bookkeeping.
    score: Optional[float] = None
    parent_id: Optional[int] = None
    id: Optional[int] = None

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls("system", content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls("assistant", content)

    def __str__(self) -> str:
        bold = "\033[1m"
        grey = "\033[37m"
        reset = "\033[0m"

        if self.role == "user":
            return f'{bold}USER INPUT:{reset} {grey}"{self.content}"{reset}'
        if self.role == "assistant":
            return f'{bold}ASSISTANT OUTPUT:{reset} {grey}"{self.content}"{reset}'
        if self.role == "system":
            return f'{bold}SYSTEM MESSAGE:{reset} {grey}"{self.content}"{reset}'

        return f"{bold}{self.role.upper()}:{reset} {grey}{self.content or ''}{reset}"

    def __hash__(self) -> int:
        return hash((self.role, self.content))
