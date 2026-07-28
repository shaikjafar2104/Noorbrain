from __future__ import annotations

import importlib.util
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List


class VoiceQA:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.report_path = self.project_root / "data" / "voice_qa_report.json"
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _check(name: str, function: Callable[[], Any], required: bool = True) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            detail = function()
            passed = True
            reason = None
        except Exception as exc:
            detail = None
            passed = False
            reason = str(exc)
        return {
            "name": name,
            "required": required,
            "passed": passed,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "detail": detail,
            "reason": reason,
        }

    @staticmethod
    def _database_check(path: Path) -> Dict[str, Any]:
        if not path.is_file():
            raise RuntimeError(f"database missing: {path}")
        with sqlite3.connect(path, timeout=3) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"database integrity: {integrity}")
            table_count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        return {"path": str(path), "integrity": integrity, "table_count": table_count}

    @staticmethod
    def _component_status(component: Any, name: str) -> Dict[str, Any]:
        status = component.status()
        if not isinstance(status, dict):
            raise RuntimeError(f"{name}.status() did not return a dictionary")
        return status

    def run(self, orchestrator: Any, include_hardware: bool = False) -> Dict[str, Any]:
        started = time.perf_counter()
        voice_dir = self.project_root / "services" / "voice_ai"

        checks: List[Dict[str, Any]] = [
            self._check("health", orchestrator.health),
            self._check("settings", lambda: orchestrator.settings_store.load().model_dump()),
            self._check("conversation_database", lambda: self._database_check(Path(orchestrator.conversation.db_path))),
            self._check("stt_status", lambda: self._component_status(orchestrator.stt, "stt")),
            self._check("tts_status", lambda: self._component_status(orchestrator.tts, "tts")),
            self._check("speaker_status", lambda: self._component_status(orchestrator.speaker, "speaker")),
            self._check("memory_status", lambda: self._component_status(orchestrator.memory, "memory")),
            self._check(
                "python314_compatibility",
                lambda: {
                    "audioop_imports": self._find_audioop_imports(voice_dir),
                    "compatible": not self._find_audioop_imports(voice_dir),
                },
            ),
            self._check(
                "optional_packages",
                lambda: {
                    name: importlib.util.find_spec(name) is not None
                    for name in ("sounddevice", "vosk", "pyttsx3")
                },
                required=False,
            ),
        ]

        if include_hardware:
            checks.append(
                self._check(
                    "microphone_hardware",
                    lambda: orchestrator.audio.list_input_devices(),
                    required=False,
                )
            )
            checks.append(
                self._check(
                    "speaker_hardware",
                    lambda: orchestrator.speaker.list_output_devices(),
                    required=False,
                )
            )

        # audioop compatibility is a real failure when imports remain.
        for check in checks:
            if check["name"] == "python314_compatibility" and check["detail"].get("audioop_imports"):
                check["passed"] = False
                check["reason"] = "active audioop imports found"

        required_failed = sum(1 for check in checks if check["required"] and not check["passed"])
        passed = sum(1 for check in checks if check["passed"])
        failed = len(checks) - passed
        report = {
            "status": "PASS" if required_failed == 0 else "FAIL",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "include_hardware": include_hardware,
            "tests_total": len(checks),
            "tests_passed": passed,
            "tests_failed": failed,
            "required_failed": required_failed,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "checks": checks,
        }
        self.report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    @staticmethod
    def _find_audioop_imports(voice_dir: Path) -> List[str]:
        matches: List[str] = []
        for path in sorted(voice_dir.glob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("import audioop") or stripped.startswith("from audioop"):
                    matches.append(f"{path.name}:{number}")
        return matches

    def latest(self) -> Dict[str, Any]:
        if not self.report_path.is_file():
            return {"status": "not_run", "path": str(self.report_path)}
        try:
            return json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {"status": "unavailable", "path": str(self.report_path), "reason": str(exc)}


voice_qa = VoiceQA()
