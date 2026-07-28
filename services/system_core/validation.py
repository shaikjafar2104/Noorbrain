"""Non-destructive startup validation for NoorBrain."""
from __future__ import annotations

from pathlib import Path
import os
import sqlite3

from .migrations import DEFAULT_DB_PATH

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StartupValidator:
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root

    def run(self) -> dict:
        checks: list[dict] = []
        self._check_directory("project_root", self.project_root, checks)
        self._check_directory("services", self.project_root / "services", checks)
        self._check_directory("config", self.project_root / "config", checks)
        self._check_directory("logs", self.project_root / "logs", checks, create=True)
        self._check_directory("backups", self.project_root / "backups", checks, create=True)
        self._check_writable(self.project_root, checks)
        self._check_database(DEFAULT_DB_PATH, checks)
        self._check_main(checks)

        failed = [item for item in checks if item["status"] == "fail"]
        warnings = [item for item in checks if item["status"] == "warning"]
        return {
            "status": "healthy" if not failed else "degraded",
            "passed": len(checks) - len(failed) - len(warnings),
            "warnings": len(warnings),
            "failed": len(failed),
            "checks": checks,
        }

    @staticmethod
    def _check_directory(name: str, path: Path, checks: list, create: bool = False) -> None:
        if create:
            path.mkdir(parents=True, exist_ok=True)
        checks.append({
            "name": name,
            "status": "pass" if path.is_dir() else "fail",
            "detail": str(path),
        })

    @staticmethod
    def _check_writable(path: Path, checks: list) -> None:
        checks.append({
            "name": "project_writable",
            "status": "pass" if os.access(path, os.W_OK) else "fail",
            "detail": str(path),
        })

    @staticmethod
    def _check_database(path: Path, checks: list) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(path), timeout=5) as conn:
                result = conn.execute("PRAGMA quick_check").fetchone()
            ok = bool(result and result[0] == "ok")
            checks.append({
                "name": "database_quick_check",
                "status": "pass" if ok else "fail",
                "detail": result[0] if result else "no result",
            })
        except Exception as exc:
            checks.append({
                "name": "database_quick_check",
                "status": "fail",
                "detail": str(exc),
            })

    def _check_main(self, checks: list) -> None:
        path = self.project_root / "main.py"
        checks.append({
            "name": "main_py",
            "status": "pass" if path.is_file() and path.stat().st_size > 0 else "fail",
            "detail": str(path),
        })


startup_validator = StartupValidator()
