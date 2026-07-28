from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict


class VoiceDiagnostics:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.voice_dir = self.project_root / "services" / "voice_ai"
        self.data_dir = self.project_root / "data"
        self.voice_db = self.data_dir / "voice.db"
        self.settings_file = self.data_dir / "voice_settings.json"
        self.vosk_model = self.project_root / "models" / "vosk"

    @staticmethod
    def _package(name: str) -> Dict[str, Any]:
        return {"name": name, "installed": importlib.util.find_spec(name) is not None}

    @staticmethod
    def _command(name: str) -> Dict[str, Any]:
        path = shutil.which(name)
        return {"name": name, "available": path is not None, "path": path}

    def _database(self) -> Dict[str, Any]:
        if not self.voice_db.is_file():
            return {"available": False, "path": str(self.voice_db), "integrity": "missing"}
        try:
            with sqlite3.connect(self.voice_db, timeout=3) as conn:
                integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
                tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {"available": True, "path": str(self.voice_db), "integrity": integrity, "tables": tables}
        except sqlite3.Error as exc:
            return {"available": True, "path": str(self.voice_db), "integrity": "error", "reason": str(exc)}

    def snapshot(self, probe_hardware: bool = False) -> Dict[str, Any]:
        packages = [self._package(name) for name in ("sounddevice", "vosk", "pyttsx3")]
        commands = [self._command(name) for name in ("espeak-ng", "espeak", "aplay", "arecord")]
        modules = {
            name: (self.voice_dir / f"{name}.py").is_file()
            for name in (
                "orchestrator", "routes", "audio_manager", "speaker_manager",
                "stt_engine", "tts_engine", "pipeline", "noise_filter", "vad",
                "analytics", "dashboard", "diagnostics",
            )
        }
        result: Dict[str, Any] = {
            "status": "ok",
            "python": {"version": sys.version.split()[0], "executable": sys.executable},
            "project_root": str(self.project_root),
            "packages": packages,
            "commands": commands,
            "modules": modules,
            "database": self._database(),
            "settings": {"available": self.settings_file.is_file(), "path": str(self.settings_file)},
            "vosk_model": {
                "available": self.vosk_model.is_dir() and any(self.vosk_model.iterdir()),
                "path": str(self.vosk_model),
            },
            "hardware_probe": {"requested": probe_hardware, "performed": False},
        }

        if probe_hardware:
            try:
                import sounddevice as sd  # type: ignore
                devices = sd.query_devices()
                inputs = sum(1 for device in devices if int(device.get("max_input_channels", 0)) > 0)
                outputs = sum(1 for device in devices if int(device.get("max_output_channels", 0)) > 0)
                result["hardware_probe"] = {
                    "requested": True,
                    "performed": True,
                    "status": "ok",
                    "input_devices": inputs,
                    "output_devices": outputs,
                }
            except Exception as exc:
                result["hardware_probe"] = {
                    "requested": True,
                    "performed": True,
                    "status": "unavailable",
                    "reason": str(exc),
                }
        return result


voice_diagnostics = VoiceDiagnostics()
