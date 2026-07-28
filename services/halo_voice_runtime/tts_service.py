from __future__ import annotations

import threading
import time
from typing import Any
from uuid import uuid4


class StreamingTTSService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._queue: list[dict[str, Any]] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._current: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._state = "stopped"

    def enqueue(
        self,
        text: str,
        *,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise ValueError("TTS text is empty.")

        item = {
            "id": uuid4().hex,
            "text": clean,
            "priority": int(priority),
            "status": "queued",
            "metadata": metadata or {},
            "created_at": time.time(),
        }

        with self._lock:
            self._queue.append(item)
            self._queue.sort(
                key=lambda value: (
                    -int(value["priority"]),
                    float(value["created_at"]),
                )
            )

        return dict(item)

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()

            self._stop.clear()
            self._state = "starting"
            self._thread = threading.Thread(
                target=self._run,
                name="NoorBrainStreamingTTS",
                daemon=True,
            )
            self._thread.start()

        return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        with self._lock:
            self._state = "stopping"
        return self.status()

    def interrupt(self) -> dict[str, Any]:
        with self._lock:
            interrupted = self._current
            self._current = None

            for item in self._queue:
                if item["status"] == "queued":
                    item["status"] = "cancelled"

        try:
            from services.voice_os.tts_worker import tts_worker
            tts_worker.stop()
        except Exception:
            pass

        return {
            "status": "interrupted",
            "current": interrupted,
        }

    def _next(self) -> dict[str, Any] | None:
        with self._lock:
            item = next(
                (
                    value
                    for value in self._queue
                    if value["status"] == "queued"
                ),
                None,
            )

            if item is None:
                return None

            item["status"] = "speaking"
            self._current = item
            return item

    def _run(self) -> None:
        self._state = "running"

        while not self._stop.is_set():
            item = self._next()

            if item is None:
                self._stop.wait(0.1)
                continue

            try:
                from services.voice_os.offline_tts import offline_tts
                result = offline_tts.speak(item["text"])
            except Exception as exc:
                result = {
                    "status": "error",
                    "reason": f"{type(exc).__name__}: {exc}",
                }

            with self._lock:
                item["status"] = (
                    "done"
                    if result.get("status") == "ok"
                    else "degraded"
                )
                item["result"] = result
                self._last_result = result
                self._current = None

        self._state = "stopped"

    def queue(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._queue]

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._state,
                "thread_alive": bool(
                    self._thread and self._thread.is_alive()
                ),
                "current": dict(self._current) if self._current else None,
                "queue_count": len(
                    [
                        item
                        for item in self._queue
                        if item["status"] == "queued"
                    ]
                ),
                "last_result": self._last_result,
            }


streaming_tts_service = StreamingTTSService()
