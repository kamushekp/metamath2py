from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class StepJsonlLogger:
    """Append-only JSONL logger for full step snapshots."""

    def __init__(self, path: Path, *, truncate_on_start: bool):
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if truncate_on_start else "a"
        with self.path.open(mode, encoding="utf-8"):
            pass

    def log(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            line = json.dumps(payload, ensure_ascii=False)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.write("\n")

    def log_session_start(self, *, session_config_path: str, runtime_config: Dict[str, Any], initial_snapshot: Dict[str, Any]) -> None:
        self.log(
            {
                "event": "session_start",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "session_config_path": session_config_path,
                "runtime_config": runtime_config,
                "initial_snapshot": initial_snapshot,
            }
        )

    def log_step_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.log(
            {
                "event": "step_snapshot",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "step_index": snapshot.get("runtime", {}).get("step_index"),
                "status": snapshot.get("status"),
                "snapshot": snapshot,
            }
        )
