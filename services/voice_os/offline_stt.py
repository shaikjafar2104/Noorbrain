from __future__ import annotations

import tempfile
import threading
import wave
from pathlib import Path
from typing import Any

from .device_config import voice_device_config


class OfflineSTT:
    def __init__(self) -> None:
        self._model = None
        self._model_lock = threading.RLock()

        self._model_path = (
            Path(__file__).resolve().parents[2]
            / "models"
            / "faster-whisper-tiny.en"
        )

    def _get_model(self):
        with self._model_lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    str(self._model_path),
                    device="cpu",
                    compute_type="int8",
                )

            return self._model

    def health(self) -> dict[str, Any]:
        try:
            import faster_whisper  # noqa: F401

            available = self._model_path.is_dir()

            return {
                "status": "healthy" if available else "degraded",
                "available_backends": (
                    ["faster_whisper"] if available else []
                ),
                "details": {
                    "faster_whisper": (
                        "available"
                        if available
                        else f"model missing: {self._model_path}"
                    )
                },
                "model": str(self._model_path),
                "config": voice_device_config.read(),
            }

        except Exception as exc:
            return {
                "status": "degraded",
                "available_backends": [],
                "details": {
                    "faster_whisper":
                        f"{type(exc).__name__}: {exc}"
                },
                "config": voice_device_config.read(),
            }

    def transcribe_pcm16(
        self,
        audio: bytes,
        *,
        sample_rate: int | None = None,
        channels: int | None = None,
        backend: str | None = None,
    ) -> dict[str, Any]:

        if not audio:
            raise ValueError("No PCM audio received.")

        config = voice_device_config.read()

        sample_rate = int(
            sample_rate or config.get("sample_rate", 16000)
        )
        channels = int(
            channels or config.get("channels", 1)
        )

        try:
            model = self._get_model()

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "noor.wav"

                with wave.open(str(path), "wb") as handle:
                    handle.setnchannels(channels)
                    handle.setsampwidth(2)
                    handle.setframerate(sample_rate)
                    handle.writeframes(audio)

                segments, info = model.transcribe(
                    str(path),
                    language="en",
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    vad_filter=False,
                    condition_on_previous_text=False,
                )

                text = " ".join(
                    segment.text.strip()
                    for segment in segments
                    if segment.text.strip()
                ).strip()

            return {
                "status": "ok",
                "text": text,
                "backend": "faster_whisper",
                "language": getattr(info, "language", "en"),
            }

        except Exception as exc:
            return {
                "status": "error",
                "text": "",
                "backend": "faster_whisper",
                "reason": f"{type(exc).__name__}: {exc}",
            }


offline_stt = OfflineSTT()
