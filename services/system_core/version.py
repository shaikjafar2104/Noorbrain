"""Central NoorBrain release/build metadata."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.8.5-rc1"
RELEASE_CHANNEL = "release-candidate"
DATABASE_SCHEMA_TARGET = 1
BUILD_DATE = "2026-07-24"


def _git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        value = result.stdout.strip()
        return value or None
    except (OSError, subprocess.SubprocessError):
        return None


def build_info() -> dict:
    return {
        "name": "NoorBrain",
        "version": VERSION,
        "channel": RELEASE_CHANNEL,
        "build_date": BUILD_DATE,
        "database_schema_target": DATABASE_SCHEMA_TARGET,
        "git_commit": _git_value("rev-parse", "--short", "HEAD"),
        "git_branch": _git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "python": os.sys.version.split()[0],
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
