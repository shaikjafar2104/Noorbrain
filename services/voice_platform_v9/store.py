from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class VoicePlatformStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "voice_platform_v9.json"
        self.lock = threading.RLock()
        self.sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "9.6.0",
            "selected_profile": "halo-natural",
            "settings": {
                "speech_rate": 1.0,
                "speech_pitch": 1.0,
                "speech_volume": 1.0,
                "language": "en-CA",
                "startup_speech": False,
                "duplicate_window_ms": 12000,
            },
            "profiles": [
                {"id": "halo-natural", "name": "HALO Natural", "rate": 1.0, "pitch": 1.0},
                {"id": "halo-calm", "name": "HALO Calm", "rate": 0.9, "pitch": 0.95},
                {"id": "halo-clear", "name": "HALO Clear", "rate": 1.05, "pitch": 1.0},
            ],
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            base = self.default()
            base.update(data)
            base["settings"].update(data.get("settings", {}))
            return base

    def write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
            return data

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            allowed = {
                "speech_rate", "speech_pitch", "speech_volume", "language",
                "startup_speech", "duplicate_window_ms",
            }
            for key, value in patch.items():
                if key in allowed:
                    data["settings"][key] = value
            return self.write(data)

    def select_profile(self, profile_id: str) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            profile = next((item for item in data["profiles"] if item["id"] == profile_id), None)
            if profile is None:
                raise KeyError(profile_id)
            data["selected_profile"] = profile_id
            data["settings"]["speech_rate"] = profile["rate"]
            data["settings"]["speech_pitch"] = profile["pitch"]
            return self.write(data)

    def start_session(self, source: str) -> dict[str, Any]:
        session = {
            "id": uuid4().hex,
            "source": source,
            "status": "active",
            "started_at": self.now(),
        }
        with self.lock:
            self.sessions[session["id"]] = session
        return session

    def end_session(self, session_id: str) -> dict[str, Any] | None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session["status"] = "ended"
                session["ended_at"] = self.now()
            return session


voice_platform_store = VoicePlatformStore()
