from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Verification:
    success: bool
    error_message: Optional[str] = None
