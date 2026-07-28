from __future__ import annotations

import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable

from .models import ComponentSnapshot, ComponentState


HealthProbe = Callable[[], dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComponentRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._probes: dict[str, HealthProbe] = {}
        self._last: dict[str, ComponentSnapshot] = {}

    def register(self, name: str, probe: HealthProbe) -> None:
        with self._lock:
            self._probes[name] = probe

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._probes)

    def inspect(self, name: str) -> ComponentSnapshot:
        with self._lock:
            probe = self._probes.get(name)

        if probe is None:
            return ComponentSnapshot(
                name=name,
                state=ComponentState.UNKNOWN,
                checked_at=utc_now(),
                latency_ms=0.0,
                error=f"Component probe not registered: {name}",
            )

        started = time.perf_counter()

        try:
            detail = probe()
            if not isinstance(detail, dict):
                detail = {"value": detail}

            raw_status = str(detail.get("status", "healthy")).casefold()

            if raw_status in {"healthy", "ok", "ready", "running", "pass"}:
                state = ComponentState.HEALTHY
            elif raw_status in {"degraded", "warning", "partial"}:
                state = ComponentState.DEGRADED
            elif raw_status in {"unavailable", "offline", "stopped"}:
                state = ComponentState.UNAVAILABLE
            else:
                state = ComponentState.HEALTHY

            snapshot = ComponentSnapshot(
                name=name,
                state=state,
                checked_at=utc_now(),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                detail=detail,
            )
        except Exception as exc:
            snapshot = ComponentSnapshot(
                name=name,
                state=ComponentState.ERROR,
                checked_at=utc_now(),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                error=f"{type(exc).__name__}: {exc}",
            )

        with self._lock:
            self._last[name] = snapshot

        return snapshot

    def inspect_all(self) -> list[ComponentSnapshot]:
        return [self.inspect(name) for name in self.names()]

    def last(self) -> list[ComponentSnapshot]:
        with self._lock:
            return [
                self._last[name]
                for name in sorted(self._last)
            ]


component_registry = ComponentRegistry()
