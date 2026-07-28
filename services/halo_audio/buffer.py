from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any


class AudioRingBuffer:
    def __init__(self, max_chunks: int = 512) -> None:
        self._lock = RLock()
        self._chunks: deque[bytes] = deque(maxlen=max_chunks)
        self._received = 0
        self._dropped = 0

    def append(self, chunk: bytes) -> dict[str, Any]:
        if not chunk:
            raise ValueError("Audio chunk is empty.")

        with self._lock:
            if len(self._chunks) == self._chunks.maxlen:
                self._dropped += 1

            self._chunks.append(bytes(chunk))
            self._received += 1

        return self.status()

    def read_all(self, *, clear: bool = True) -> bytes:
        with self._lock:
            payload = b"".join(self._chunks)
            if clear:
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
                "buffered_bytes": sum(len(item) for item in self._chunks),
                "received_chunks": self._received,
                "dropped_chunks": self._dropped,
                "capacity": self._chunks.maxlen,
            }


audio_ring_buffer = AudioRingBuffer()
