from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from .models import SettingsUpdate, VoiceSettings


class VoiceSettingsStore:
    """
    Fast, Python 3.14-compatible settings storage.

    No hardware probing and no long-running lock is used.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.path = self.project_root / "data" / "voice_settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.is_file():
            self.save(VoiceSettings())

    def load(self) -> VoiceSettings:
        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            return VoiceSettings.model_validate(payload)

        except Exception:
            defaults = VoiceSettings()

            try:
                self.save(defaults)
            except Exception:
                pass

            return defaults

    def save(self, settings: VoiceSettings) -> VoiceSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = settings.model_dump()

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix="voice-settings-",
            suffix=".tmp",
            dir=str(self.path.parent),
        )

        try:
            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary_name, self.path)

        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

        return settings

    def update(
        self,
        update: SettingsUpdate | Dict[str, Any],
    ) -> VoiceSettings:
        if isinstance(update, SettingsUpdate):
            patch = update.model_dump(exclude_none=True)
        else:
            patch = {
                key: value
                for key, value in update.items()
                if value is not None
            }

        current = self.load().model_dump()
        current.update(patch)

        validated = VoiceSettings.model_validate(current)
        return self.save(validated)
