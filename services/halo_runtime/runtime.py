from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from .component_registry import component_registry
from .config_store import runtime_config_store
from .models import ComponentState, RuntimeState

from . import probes as _probes  # noqa: F401


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HALORuntimeManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state = RuntimeState.STOPPED
        self._started_at: str | None = None
        self._stopped_at: str | None = None
        self._last_heartbeat: str | None = None
        self._heartbeat_count = 0
        self._recovery_attempts: dict[str, int] = {}
        self._last_error: str | None = None

    def start(self, reason: str = "manual") -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()

            self._state = RuntimeState.STARTING
            self._stop_event.clear()
            self._started_at = utc_now()
            self._stopped_at = None
            self._last_error = None

            self._thread = threading.Thread(
                target=self._run,
                name="NoorBrainHALORuntime",
                daemon=True,
            )
            self._thread.start()

        self._start_optional_services()
        return {
            **self.status(),
            "reason": reason,
        }

    def stop(self, reason: str = "manual") -> dict[str, Any]:
        with self._lock:
            self._state = RuntimeState.STOPPING
            self._stop_event.set()

        self._stop_optional_services()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        with self._lock:
            self._state = RuntimeState.STOPPED
            self._stopped_at = utc_now()

        return {
            **self.status(),
            "reason": reason,
        }

    def restart(self, reason: str = "manual") -> dict[str, Any]:
        self.stop(reason=f"restart:{reason}")
        return self.start(reason=f"restart:{reason}")

    def _run(self) -> None:
        with self._lock:
            self._state = RuntimeState.RUNNING

        while not self._stop_event.is_set():
            try:
                self.heartbeat()
            except Exception as exc:
                with self._lock:
                    self._state = RuntimeState.ERROR
                    self._last_error = f"{type(exc).__name__}: {exc}"

            interval = runtime_config_store.read().heartbeat_interval_seconds
            self._stop_event.wait(interval)

        with self._lock:
            if self._state != RuntimeState.ERROR:
                self._state = RuntimeState.STOPPED

    def heartbeat(self) -> dict[str, Any]:
        snapshots = component_registry.inspect_all()
        unhealthy = [
            item
            for item in snapshots
            if item.state in {
                ComponentState.DEGRADED,
                ComponentState.UNAVAILABLE,
                ComponentState.ERROR,
            }
        ]

        config = runtime_config_store.read()

        if unhealthy and config.enable_recovery:
            for snapshot in unhealthy:
                self._attempt_recovery(snapshot.name)

        with self._lock:
            self._heartbeat_count += 1
            self._last_heartbeat = utc_now()

            if any(
                item.state == ComponentState.ERROR
                for item in snapshots
            ):
                self._state = RuntimeState.ERROR
            elif unhealthy:
                self._state = RuntimeState.DEGRADED
            else:
                self._state = RuntimeState.RUNNING

        return {
            "status": "ok",
            "runtime_state": self._state,
            "component_count": len(snapshots),
            "unhealthy_count": len(unhealthy),
            "components": [
                item.model_dump(mode="json")
                for item in snapshots
            ],
        }

    def _attempt_recovery(self, component: str) -> None:
        config = runtime_config_store.read()
        attempts = self._recovery_attempts.get(component, 0)

        if attempts >= config.max_recovery_attempts:
            return

        self._recovery_attempts[component] = attempts + 1

        if component == "voice_os":
            try:
                from services.voice_os.live_pipeline import live_voice_pipeline

                status = live_voice_pipeline.status()
                if status.get("status") == "error":
                    live_voice_pipeline.stop()
            except Exception:
                pass

    def _start_optional_services(self) -> None:
        config = runtime_config_store.read()

        if config.auto_start_voice_runtime:
            try:
                from services.voice_os.live_pipeline import live_voice_pipeline
                live_voice_pipeline.start()
            except Exception as exc:
                self._last_error = f"Voice runtime start failed: {exc}"

        if config.auto_start_tts_worker:
            try:
                from services.voice_os.tts_worker import tts_worker
                tts_worker.start()
            except Exception as exc:
                self._last_error = f"TTS worker start failed: {exc}"

    @staticmethod
    def _stop_optional_services() -> None:
        try:
            from services.voice_os.live_pipeline import live_voice_pipeline
            live_voice_pipeline.stop()
        except Exception:
            pass

        try:
            from services.voice_os.tts_worker import tts_worker
            tts_worker.stop()
        except Exception:
            pass

    def status(self) -> dict[str, Any]:
        with self._lock:
            thread_alive = bool(self._thread and self._thread.is_alive())
            state = self._state

        return {
            "status": "ok",
            "service": "halo_runtime",
            "version": "3.1-c1.1",
            "runtime_state": state,
            "thread_alive": thread_alive,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "last_heartbeat": self._last_heartbeat,
            "heartbeat_count": self._heartbeat_count,
            "last_error": self._last_error,
            "recovery_attempts": dict(self._recovery_attempts),
            "config": runtime_config_store.read().model_dump(mode="json"),
            "components": [
                item.model_dump(mode="json")
                for item in component_registry.last()
            ],
        }


halo_runtime_manager = HALORuntimeManager()
