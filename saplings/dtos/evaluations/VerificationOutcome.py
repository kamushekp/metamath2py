from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class VerificationOutcome:
    success: bool
    stage: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": bool(self.success),
            "stage": self.stage,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "VerificationOutcome":
        return cls(
            success=bool(payload.get("success", False)),
            stage=payload.get("stage"),
            error_message=payload.get("error_message"),
            metadata=dict(payload.get("metadata", {})),
        )
