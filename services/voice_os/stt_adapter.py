from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Any


class STTAdapter:
    def health(self) -> dict[str, Any]:
        backends = []

        try:
            import vosk  # type: ignore
            backends.append("vosk")
        except Exception:
            pass

        try:
            import speech_recognition  # type: ignore
            backends.append("speech_recognition")
        except Exception:
            pass

        return {
            "status": "healthy" if backends else "degraded",
            "available_backends": backends,
            "preferred": backends[0] if backends else None,
        }

    def transcribe_pcm16(
        self,
        audio: bytes,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> dict[str, Any]:
        if not audio:
            raise ValueError("No audio data received.")

        try:
            import speech_recognition as sr  # type: ignore
        except Exception as exc:
            return {
                "status": "unavailable",
                "text": "",
                "reason": f"speech_recognition unavailable: {exc}",
            }

        recognizer = sr.Recognizer()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voice.wav"

            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(channels)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(audio)

            with sr.AudioFile(str(path)) as source:
                recorded = recognizer.record(source)

            try:
                text = recognizer.recognize_sphinx(recorded)
            except Exception as exc:
                return {
                    "status": "unavailable",
                    "text": "",
                    "reason": f"offline STT failed: {exc}",
                }

        return {
            "status": "ok",
            "text": text.strip(),
            "backend": "speech_recognition+pocketsphinx",
        }


stt_adapter = STTAdapter()
