from __future__ import annotations

import threading
import time
from typing import Any

from .buffer import audio_ring_buffer
from .config_store import audio_config_store
from .device_manager import audio_device_manager


class HALOAudioService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._state = "stopped"
        self._last_error: str | None = None
        self._started_at: float | None = None

    def start(self, reason: str = "manual") -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()

            self._stop.clear()
            self._state = "starting"
            self._thread = threading.Thread(
                target=self._run,
                name="NoorBrainHALOAudio",
                daemon=True,
            )
            self._thread.start()

        result = self.status()
        result["reason"] = reason
        return result

    def stop(self, reason: str = "manual") -> dict[str, Any]:
        self._stop.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        with self._lock:
            self._state = "stopped"

        result = self.status()
        result["reason"] = reason
        return result

    def _run(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:
            self._last_error = f"sounddevice unavailable: {exc}"
            self._state = "degraded"
            return

        config = audio_config_store.read()
        self._state = "running"
        self._started_at = time.time()

        def callback(indata, frames, time_info, status) -> None:
            if status:
                self._last_error = str(status)

            try:
                chunk = bytes(indata)
                if config.input_gain != 1.0:
                    chunk = self._apply_gain_pcm16(chunk, config.input_gain)
                audio_ring_buffer.append(chunk)
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"

        try:
            with sd.RawInputStream(
                samplerate=config.sample_rate,
                channels=config.channels,
                blocksize=config.block_size,
                dtype="int16",
                device=config.input_device,
                callback=callback,
            ):
                while not self._stop.wait(0.1):
                    pass
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._state = "degraded"
            return

        self._state = "stopped"

    @staticmethod
    def _apply_gain_pcm16(data: bytes, gain: float) -> bytes:
        import array

        samples = array.array("h")
        samples.frombytes(data)

        for index, sample in enumerate(samples):
            value = int(sample * gain)
            samples[index] = max(-32768, min(32767, value))

        return samples.tobytes()

    def status(self) -> dict[str, Any]:
        return {
            "status": self._state,
            "service": "halo_audio",
            "version": "3.1-c1.2",
            "thread_alive": bool(self._thread and self._thread.is_alive()),
            "started_at": self._started_at,
            "last_error": self._last_error,
            "config": audio_config_store.read().model_dump(mode="json"),
            "buffer": audio_ring_buffer.status(),
            "devices": audio_device_manager.health(),
        }


halo_audio_service = HALOAudioService()
