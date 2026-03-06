from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional


class AutoRunner:
    """Runs search steps in the background up to a configured limit."""

    def __init__(self, *, step_fn: Callable[[], Dict[str, Any]], max_steps: int, step_delay_ms: int):
        self._step_fn = step_fn
        self.max_steps = max(1, int(max_steps))
        self.step_delay_ms = max(0, int(step_delay_ms))
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._running = False
        self._steps_done = 0
        self._last_error: Optional[str] = None

    def ensure_started(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._running = True
            self._thread = threading.Thread(target=self._run, name="web-auto-runner", daemon=True)
            self._thread.start()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "started": self._started,
                "running": self._running,
                "steps_done": self._steps_done,
                "max_steps": self.max_steps,
                "step_delay_ms": self.step_delay_ms,
                "error": self._last_error,
            }

    def _run(self) -> None:
        try:
            while True:
                with self._lock:
                    if self._steps_done >= self.max_steps:
                        self._running = False
                        return

                snapshot = self._step_fn()

                with self._lock:
                    self._steps_done += 1

                if snapshot.get("status") != "running":
                    with self._lock:
                        self._running = False
                    return

                if self.step_delay_ms > 0:
                    time.sleep(self.step_delay_ms / 1000.0)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._running = False
                self._last_error = str(exc)
