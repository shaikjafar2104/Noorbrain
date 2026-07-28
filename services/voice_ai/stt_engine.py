from __future__ import annotations
import json
import wave
from pathlib import Path
from typing import Any, Dict, Optional


class SpeechToTextEngine:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.model_dir = self.project_root / "models" / "vosk"
        self.last_error: Optional[str] = None

    def status(self) -> Dict[str, Any]:
        try:
            import vosk  # type: ignore  # noqa: F401
            installed = True
        except Exception:
            installed = False
        model_exists = self.model_dir.is_dir() and any(self.model_dir.iterdir())
        return {
            "available": installed and model_exists,
            "engine": "vosk" if installed else None,
            "package_installed": installed,
            "model_path": str(self.model_dir),
            "model_present": model_exists,
            "last_error": self.last_error,
        }

    def transcribe_wav(self, audio_path: Path) -> Dict[str, Any]:
        try:
            from vosk import KaldiRecognizer, Model  # type: ignore
            if not self.model_dir.is_dir():
                raise RuntimeError(f"Vosk model not found at {self.model_dir}")
            model = Model(str(self.model_dir))
            with wave.open(str(audio_path), "rb") as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                    raise RuntimeError("WAV must be mono 16-bit PCM")
                recognizer = KaldiRecognizer(model, wav.getframerate())
                chunks = []
                while True:
                    data = wav.readframes(4000)
                    if not data:
                        break
                    if recognizer.AcceptWaveform(data):
                        value = json.loads(recognizer.Result()).get("text", "").strip()
                        if value:
                            chunks.append(value)
                final = json.loads(recognizer.FinalResult()).get("text", "").strip()
                if final:
                    chunks.append(final)
            text = " ".join(chunks).strip()
            self.last_error = None
            return {"status": "ok", "engine": "vosk", "text": text, "audio_path": str(audio_path)}
        except Exception as exc:
            self.last_error = str(exc)
            return {"status": "unavailable", "engine": "vosk", "text": "", "reason": str(exc)}
