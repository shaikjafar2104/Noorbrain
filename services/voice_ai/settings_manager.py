from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping


class VoiceSettingsManager:
    """Safe adapter around the existing VoiceSettingsStore.

    It validates a small set of runtime fields, delegates persistence to the
    current store when possible, and falls back to an atomic JSON write.
    """

    ALLOWED_FIELDS = {
        "enabled",
        "wake_word",
        "require_wake_word",
        "language",
        "voice_name",
        "speech_rate",
        "volume",
        "sample_rate",
        "listen_seconds",
        "noise_filter_enabled",
        "vad_enabled",
    }

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.path = self.project_root / "data" / "voice_settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _dump_model(value: Any) -> Dict[str, Any]:
        if hasattr(value, "model_dump"):
            return dict(value.model_dump())
        if hasattr(value, "dict"):
            return dict(value.dict())
        if isinstance(value, Mapping):
            return dict(value)
        return {
            key: getattr(value, key)
            for key in dir(value)
            if not key.startswith("_") and not callable(getattr(value, key, None))
        }

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        clean = {key: value for key, value in data.items() if key in VoiceSettingsManager.ALLOWED_FIELDS}

        if "wake_word" in clean:
            wake_word = " ".join(str(clean["wake_word"]).strip().split())
            if not wake_word or len(wake_word) > 64:
                raise ValueError("wake_word must contain 1 to 64 characters")
            clean["wake_word"] = wake_word

        if "language" in clean:
            language = str(clean["language"]).strip()
            if not language or len(language) > 32:
                raise ValueError("language must contain 1 to 32 characters")
            clean["language"] = language

        if "voice_name" in clean and clean["voice_name"] is not None:
            clean["voice_name"] = str(clean["voice_name"]).strip() or None

        if "volume" in clean:
            volume = float(clean["volume"])
            if not 0.0 <= volume <= 1.0:
                raise ValueError("volume must be between 0.0 and 1.0")
            clean["volume"] = volume

        if "speech_rate" in clean:
            rate = int(clean["speech_rate"])
            if not 50 <= rate <= 400:
                raise ValueError("speech_rate must be between 50 and 400")
            clean["speech_rate"] = rate

        if "sample_rate" in clean:
            sample_rate = int(clean["sample_rate"])
            if sample_rate not in {8000, 16000, 22050, 32000, 44100, 48000}:
                raise ValueError("unsupported sample_rate")
            clean["sample_rate"] = sample_rate

        if "listen_seconds" in clean:
            seconds = float(clean["listen_seconds"])
            if not 1.0 <= seconds <= 30.0:
                raise ValueError("listen_seconds must be between 1 and 30")
            clean["listen_seconds"] = seconds

        for key in ("enabled", "require_wake_word", "noise_filter_enabled", "vad_enabled"):
            if key in clean:
                clean[key] = bool(clean[key])

        if not clean:
            raise ValueError("no supported settings supplied")
        return clean

    def get(self, store: Any) -> Dict[str, Any]:
        settings = self._dump_model(store.load())
        return {
            "status": "ok",
            "settings": settings,
            "path": str(self.path),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def update(self, store: Any, values: Mapping[str, Any]) -> Dict[str, Any]:
        clean = self._validate(dict(values))

        # Prefer the project's existing Pydantic update path.
        try:
            from .models import SettingsUpdate

            payload = SettingsUpdate(**clean)
            updated = store.update(payload)
            settings = self._dump_model(updated)
        except Exception:
            current = self._dump_model(store.load())
            current.update(clean)
            self._atomic_json_write(current)
            settings = current

        return {
            "status": "ok",
            "settings": settings,
            "changed": sorted(clean),
            "path": str(self.path),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _atomic_json_write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="voice-settings-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


voice_settings_manager = VoiceSettingsManager()
