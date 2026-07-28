from __future__ import annotations

import base64
from collections import deque
from threading import RLock
from typing import Any


class AudioStreamBuffer:
    def __init__(self, max_chunks: int = 256) -> None:
        self._lock = RLock()
        self._chunks: deque[bytes] = deque(maxlen=max_chunks)
        self._dropped = 0
        self._received = 0

    def append(self, chunk: bytes) -> dict[str, Any]:
        if not chunk:
            raise ValueError("Audio chunk is empty.")

        with self._lock:
            if len(self._chunks) == self._chunks.maxlen:
                self._dropped += 1

            self._chunks.append(bytes(chunk))
            self._received += 1

            return self.status()

    def append_base64(self, encoded: str) -> dict[str, Any]:
        try:
            chunk = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError(f"Invalid base64 audio: {exc}") from exc

        return self.append(chunk)

    def pop_all(self) -> bytes:
        with self._lock:
            payload = b"".join(self._chunks)
            self._chunks.clear()
            return payload

    def clear(self) -> int:
        with self._lock:
            count = len(self._chunks)
            self._chunks.clear()
            return count

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "ready",
                "buffered_chunks": len(self._chunks),
                "buffered_bytes": sum(len(chunk) for chunk in self._chunks),
                "received_chunks": self._received,
                "dropped_chunks": self._dropped,
                "capacity": self._chunks.maxlen,
            }


audio_stream_buffer = AudioStreamBuffer()
