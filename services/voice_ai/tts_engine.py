from __future__ import annotations
import threading
from typing import Any, Dict, Optional


class TextToSpeechEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None
        self.last_text: Optional[str] = None

    @staticmethod
    def status() -> Dict[str, Any]:
        try:
            import pyttsx3  # type: ignore  # noqa: F401
            return {"available": True, "engine": "pyttsx3"}
        except Exception as exc:
            return {"available": False, "engine": None, "reason": str(exc)}

    def speak(self, text: str, rate: int = 165, volume: float = 1.0, voice_name: str | None = None,
              blocking: bool = False) -> Dict[str, Any]:
        self.last_text = text
        availability = self.status()
        if not availability.get("available"):
            return {"status": "unavailable", "spoken": False, "text": text, "reason": availability.get("reason")}

        def worker() -> None:
            try:
                import pyttsx3  # type: ignore
                with self._lock:
                    engine = pyttsx3.init()
                    engine.setProperty("rate", rate)
                    engine.setProperty("volume", volume)
                    if voice_name:
                        for voice in engine.getProperty("voices"):
                            if voice_name.lower() in str(voice.name).lower():
                                engine.setProperty("voice", voice.id); break
                    engine.say(text)
                    engine.runAndWait()
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)

        if blocking:
            worker()
            return {"status": "ok" if not self.last_error else "error", "spoken": not bool(self.last_error),
                    "text": text, "error": self.last_error}
        threading.Thread(target=worker, daemon=True, name="noorbrain-tts").start()
        return {"status": "queued", "spoken": True, "text": text}
