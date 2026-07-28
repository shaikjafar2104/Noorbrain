from __future__ import annotations

import json
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

from .device_config import voice_device_config


class OfflineSTT:
    def health(self) -> dict[str, Any]:
        backends: dict[str, str] = {}

        try:
            import vosk  # type: ignore
            backends["vosk"] = "available"
        except Exception as exc:
            backends["vosk"] = f"unavailable: {exc}"

        try:
            import speech_recognition  # type: ignore
            backends["speech_recognition"] = "available"
        except Exception as exc:
            backends["speech_recognition"] = f"unavailable: {exc}"

        available = [
            name for name, state in backends.items()
            if state == "available"
        ]

        return {
            "status": "healthy" if available else "degraded",
            "available_backends": available,
            "details": backends,
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
        sample_rate = int(sample_rate or config.get("sample_rate", 16000))
        channels = int(channels or config.get("channels", 1))
        backend = str(backend or config.get("stt_backend", "auto"))

        if backend in {"auto", "vosk"}:
            result = self._vosk(audio, sample_rate)
            if result["status"] == "ok" or backend == "vosk":
                return result

        if backend in {"auto", "speech_recognition"}:
            return self._speech_recognition(audio, sample_rate, channels)

        return {
            "status": "unavailable",
            "text": "",
            "reason": f"Unsupported STT backend: {backend}",
        }

    def _vosk(self, audio: bytes, sample_rate: int) -> dict[str, Any]:
        try:
            from vosk import KaldiRecognizer, Model  # type: ignore
        except Exception as exc:
            return {
                "status": "unavailable",
                "text": "",
                "backend": "vosk",
                "reason": str(exc),
            }

        model_path = os.getenv("VOSK_MODEL_PATH", "").strip()
        if not model_path or not Path(model_path).is_dir():
            return {
                "status": "unavailable",
                "text": "",
                "backend": "vosk",
                "reason": "VOSK_MODEL_PATH is not configured.",
            }

        try:
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, sample_rate)
            recognizer.AcceptWaveform(audio)
            payload = json.loads(recognizer.FinalResult())
            text = str(payload.get("text") or "").strip()
        except Exception as exc:
            return {
                "status": "error",
                "text": "",
                "backend": "vosk",
                "reason": f"{type(exc).__name__}: {exc}",
            }

        return {
            "status": "ok",
            "text": text,
            "backend": "vosk",
        }

    def _speech_recognition(
        self,
        audio: bytes,
        sample_rate: int,
        channels: int,
    ) -> dict[str, Any]:
        try:
            import speech_recognition as sr  # type: ignore
        except Exception as exc:
            return {
                "status": "unavailable",
                "text": "",
                "backend": "speech_recognition",
                "reason": str(exc),
            }

        recognizer = sr.Recognizer()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voice.wav"

            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(channels)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(audio)

            try:
                with sr.AudioFile(str(path)) as source:
                    recorded = recognizer.record(source)
                text = recognizer.recognize_sphinx(recorded).strip()
            except Exception as exc:
                return {
                    "status": "unavailable",
                    "text": "",
                    "backend": "speech_recognition+pocketsphinx",
                    "reason": f"{type(exc).__name__}: {exc}",
                }

        return {
            "status": "ok",
            "text": text,
            "backend": "speech_recognition+pocketsphinx",
        }


offline_stt = OfflineSTT()
