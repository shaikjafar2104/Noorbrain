from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable


class NoorWatchdog:
    """Passive watchdog: records failures without killing or restarting the app."""

    def __init__(self, interval_seconds: int = 30) -> None:
        self.interval_seconds = max(10, interval_seconds)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._check: Callable[[], dict[str, Any]] | None = None
        self._state: dict[str, Any] = {
            "running": False,
            "checks": 0,
            "consecutive_failures": 0,
            "last_check_at": None,
            "last_status": "not_started",
            "last_error": None,
        }

    def start(self, check: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._check = check
            self._stop.clear()
            self._state["running"] = True
            self._thread = threading.Thread(target=self._loop, name="noorbrain-watchdog", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2)
        with self._lock:
            self._state["running"] = False

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.run_once()

    def run_once(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        try:
            result = self._check() if self._check else {"status": "unconfigured"}
            status = result.get("status", "unknown")
            failure = status not in {"healthy", "ok"}
            with self._lock:
                self._state["checks"] += 1
                self._state["last_check_at"] = now
                self._state["last_status"] = status
                self._state["last_error"] = None
                self._state["consecutive_failures"] = self._state["consecutive_failures"] + 1 if failure else 0
        except Exception as exc:
            with self._lock:
                self._state["checks"] += 1
                self._state["last_check_at"] = now
                self._state["last_status"] = "error"
                self._state["last_error"] = str(exc)
                self._state["consecutive_failures"] += 1
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)


watchdog = NoorWatchdog()
