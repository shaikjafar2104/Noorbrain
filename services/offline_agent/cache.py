from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get_or_set(
        self,
        key: str,
        ttl_seconds: float,
        producer: Callable[[], Any],
    ) -> Any:
        now = time.monotonic()

        with self._lock:
            cached = self._items.get(key)
            if cached is not None and cached[0] > now:
                return cached[1]

        value = producer()

        with self._lock:
            self._items[key] = (now + max(0.0, ttl_seconds), value)

        return value

    def clear(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._items.clear()
                return

            for key in list(self._items):
                if key.startswith(prefix):
                    self._items.pop(key, None)


agent_cache = TTLCache()
