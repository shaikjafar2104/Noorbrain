from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "noor_settings.json"


DEFAULTS: dict[str, Any] = {
    "assistant": {
        "name": "Noor",
        "wake_words": [
            "noor",
            "hey noor",
            "hello noor",
        ],
        "response_style": "short",
        "follow_up_enabled": True,
        "confirmation_enabled": True,
    },

    "voice": {
        "enabled": True,
        "language": "en-US",
        "rate": 0.95,
        "pitch": 1.0,
        "volume": 1.0,
        "wake_sensitivity": 120,
        "interrupt_enabled": True,
    },

    "ai": {
        "mode": "local_first",
        "local_model": "llama3.2:3b",
        "fallback_online": False,
        "context_size": 1024,
        "max_response_tokens": 40,
    },

    "islamic": {
        "prayer_reminders": True,
        "adhan_enabled": True,
        "dua_reminders": True,
        "azkar_reminders": True,
    },

    "privacy": {
        "camera_enabled": True,
        "microphone_enabled": True,
        "activity_learning": True,
        "face_recognition": True,
    },

    "notifications": {
        "mobile_enabled": True,
        "dashboard_enabled": True,
    },

    "system": {
        "developer_mode": False,
    },
}


class NoorSettings:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        STORE.parent.mkdir(parents=True, exist_ok=True)

        if not STORE.exists():
            self._write(deepcopy(DEFAULTS))

        self._repair()

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(STORE.read_text())
        except Exception:
            data = {}

        return data if isinstance(data, dict) else {}

    def _write(self, data: dict[str, Any]) -> None:
        temp = STORE.with_suffix(".tmp")

        temp.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        temp.replace(STORE)

    def _merge_defaults(
        self,
        target: dict[str, Any],
        defaults: dict[str, Any],
    ) -> bool:
        changed = False

        for key, value in defaults.items():
            if key not in target:
                target[key] = deepcopy(value)
                changed = True

            elif (
                isinstance(value, dict)
                and isinstance(target.get(key), dict)
            ):
                if self._merge_defaults(
                    target[key],
                    value,
                ):
                    changed = True

        return changed

    def _repair(self) -> None:
        with self._lock:
            data = self._read()

            if self._merge_defaults(
                data,
                deepcopy(DEFAULTS),
            ):
                self._write(data)

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            self._repair()
            return deepcopy(self._read())

    def get_section(
        self,
        section: str,
    ) -> dict[str, Any]:
        data = self.get_all()
        value = data.get(section)

        if not isinstance(value, dict):
            raise KeyError(section)

        return deepcopy(value)

    def update_section(
        self,
        section: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            data = self._read()

            current = data.get(section)

            if not isinstance(current, dict):
                raise KeyError(section)

            current.update(values)

            self._write(data)

            return deepcopy(current)

    def update_all(
        self,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            data = self._read()

            for section, section_values in values.items():
                if (
                    section in data
                    and isinstance(data[section], dict)
                    and isinstance(section_values, dict)
                ):
                    data[section].update(section_values)

            self._write(data)

            return deepcopy(data)

    def reset(self) -> dict[str, Any]:
        with self._lock:
            data = deepcopy(DEFAULTS)
            self._write(data)
            return deepcopy(data)


noor_settings = NoorSettings()
