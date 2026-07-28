from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.8.5-rc1"
BUILD = "20260724"


def _exists(relative: str) -> bool:
    return (PROJECT_ROOT / relative).exists()


def _latest_qa() -> dict[str, Any]:
    path = PROJECT_ROOT / "reports" / "qa" / "latest.json"
    if not path.exists():
        return {"status": "not-run"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid"}


def checklist() -> list[dict[str, Any]]:
    qa = _latest_qa()
    return [
        {"name": "main_application", "passed": _exists("main.py")},
        {"name": "dashboard", "passed": _exists("dashboard/index.html")},
        {"name": "database", "passed": _exists("noorbrain.db")},
        {"name": "memory_engine", "passed": _exists("services/ai_memory")},
        {"name": "qa_automation", "passed": _exists("services/qa")},
        {"name": "release_manager", "passed": _exists("services/release")},
        {"name": "restart_script", "passed": _exists("restart_noorbrain.sh")},
        {"name": "latest_qa_passed", "passed": qa.get("status") == "passed"},
    ]


def release_status() -> dict[str, Any]:
    items = checklist()
    passed = sum(bool(item["passed"]) for item in items)
    ready = passed == len(items)
    return {
        "status": "ready" if ready else "attention-required",
        "ready_for_sprint_9": ready,
        "version": VERSION,
        "build": BUILD,
        "release_channel": "release-candidate",
        "checks_passed": passed,
        "checks_total": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def release_summary() -> dict[str, Any]:
    return {
        **release_status(),
        "name": "NoorBrain",
        "milestone": "Sprint 8.5",
        "components": [
            "versioning and migrations",
            "health monitoring and watchdog",
            "backup and log operations",
            "automated QA and benchmark",
            "release-candidate validation",
        ],
    }
