from __future__ import annotations

import threading
import time
from typing import Any

from .adapters import tts_speak
from .queue import voice_queue


class TTSWorker:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._last_result: dict[str, Any] | None = None

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()

            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="NoorBrainVoiceTTS",
                daemon=True,
            )
            self._thread.start()
            return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        return self.status()

    def _run(self) -> None:
        while not self._stop.is_set():
            item = voice_queue.next()

            if item is None:
                time.sleep(0.15)
                continue

            try:
                result = tts_speak(str(item.get("text") or ""))
                self._last_result = result
            finally:
                try:
                    voice_queue.complete(str(item["id"]))
                except Exception:
                    pass

    def status(self) -> dict[str, Any]:
        return {
            "status": "running"
            if self._thread and self._thread.is_alive()
            else "stopped",
            "last_result": self._last_result,
        }


tts_worker = TTSWorker()
