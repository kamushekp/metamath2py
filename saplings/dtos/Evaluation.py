# Standard library
from typing import Optional

# Third party (optional at import time)
try:  # pragma: no cover - optional dependency
    import json_repair  # type: ignore
except Exception:  # pragma: no cover
    json_repair = None
    import json as _json

# Local
from saplings.dtos.Message import Message


class Evaluation(object):
    def __init__(self, score: int, reasoning: Optional[str] = None):
        self.score = score
        self.reasoning = reasoning

    def to_message(self) -> Message:
        return Message.user(f"Reasoning: {self.reasoning}\nScore: {self.score * 10}")

    @classmethod
    def from_message(cls, message: Message) -> "Evaluation":
        if json_repair is not None:
            arguments = json_repair.loads(message.content)
        else:
            try:
                arguments = _json.loads(message.content)
            except Exception:
                arguments = {"score": 5, "reasoning": message.content}
        reasoning = arguments.get("reasoning", "")
        score = arguments.get("score", 5)
        score = max(0, min(score, 10))  # Ensures score is between 0 and 10
        score = score / 10.0  # Normalizes score to be between 0 and 1
        return cls(score, reasoning)
