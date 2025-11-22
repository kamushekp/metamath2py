from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Verification:
    success: bool
    error_message: Optional[str] = None
