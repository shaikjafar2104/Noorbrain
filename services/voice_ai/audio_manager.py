from __future__ import annotations

import importlib.util
import threading
import time
import wave
from pathlib import Path
from typing import Any, Dict, Optional


class AudioManager:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.audio_dir = self.project_root / "data" / "voice_audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self.last_error: Optional[str] = None
        self.last_recording: Optional[str] = None

    @staticmethod
    def backend_status() -> Dict[str, Any]:
        """
        Lightweight status check.

        Do not call sounddevice.query_devices() here because ALSA/PortAudio
        device probing can block the FastAPI health endpoint.
        """
        installed = importlib.util.find_spec("sounddevice") is not None

        return {
            "available": installed,
            "backend": "sounddevice" if installed else None,
            "package_installed": installed,
            "device_probe": "deferred",
            "input_devices": [],
        }

    @staticmethod
    def list_input_devices() -> Dict[str, Any]:
        """
        Explicit device probe. This may take time on some Linux systems,
        so it is never called by the health endpoint.
        """
        try:
            import sounddevice as sd  # type: ignore

            devices = sd.query_devices()
            inputs = []

            for index, device in enumerate(devices):
                if int(device.get("max_input_channels", 0)) > 0:
                    inputs.append(
                        {
                            "index": index,
                            "name": str(device.get("name", "unknown")),
                            "channels": int(
                                device.get("max_input_channels", 0)
                            ),
                            "sample_rate": float(
                                device.get("default_samplerate", 0)
                            ),
                        }
                    )

            return {
                "status": "ok",
                "available": bool(inputs),
                "input_devices": inputs,
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "available": False,
                "input_devices": [],
                "reason": str(exc),
            }

    def record(self, seconds: float, sample_rate: int) -> Path:
        with self._lock:
            try:
                import sounddevice as sd  # type: ignore

                stamp = time.strftime("%Y%m%d-%H%M%S")
                path = self.audio_dir / f"recording-{stamp}.wav"

                frames = int(seconds * sample_rate)

                data = sd.rec(
                    frames,
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()

                with wave.open(str(path), "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(data.tobytes())

                self.last_recording = str(path)
                self.last_error = None
                return path

            except Exception as exc:
                self.last_error = str(exc)
                raise RuntimeError(
                    f"Microphone recording unavailable: {exc}"
                ) from exc

    def snapshot(self) -> Dict[str, Any]:
        status = self.backend_status()
        status.update(
            {
                "last_recording": self.last_recording,
                "last_error": self.last_error,
            }
        )
        return status
