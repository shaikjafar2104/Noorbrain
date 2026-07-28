from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutomationBackupManager:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.data_dir = self.project_root / "data"
        self.backup_dir = self.project_root / "backups" / "automation"
        self.export_dir = self.project_root / "exports" / "automation"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.managed_files = {
            "devices": self.data_dir / "devices.json",
            "esp32": self.data_dir / "esp32_devices.json",
            "rules": self.data_dir / "automation_rules.json",
            "scenes": self.data_dir / "automation_scenes.json",
            "groups": self.data_dir / "device_groups.json",
            "routines": self.data_dir / "automation_routines.json",
        }

    def _validate_json_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {
                "exists": False,
                "valid": True,
                "path": str(path),
                "reason": "missing_optional_file",
            }

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {
                "exists": True,
                "valid": isinstance(payload, dict),
                "path": str(path),
                "schema_version": payload.get("schema_version"),
            }
        except Exception as exc:
            return {
                "exists": True,
                "valid": False,
                "path": str(path),
                "reason": f"{type(exc).__name__}: {exc}",
            }

    def validate_current(self) -> dict[str, Any]:
        files = {
            name: self._validate_json_file(path)
            for name, path in self.managed_files.items()
        }
        return {
            "status": "ok" if all(item["valid"] for item in files.values()) else "invalid",
            "files": files,
        }

    def create_backup(self, label: str | None = None) -> dict[str, Any]:
        validation = self.validate_current()
        if validation["status"] != "ok":
            raise ValueError("Current automation configuration contains invalid JSON.")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(
            char if char.isalnum() or char in "-_" else "-"
            for char in (label or "manual")
        ).strip("-") or "manual"

        target = self.backup_dir / f"automation-{safe_label}-{stamp}.zip"

        manifest = {
            "schema_version": 1,
            "created_at": utc_now(),
            "label": safe_label,
            "files": [],
        }

        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in self.managed_files.items():
                if not path.exists():
                    continue
                archive_name = f"data/{path.name}"
                archive.write(path, archive_name)
                manifest["files"].append({
                    "name": name,
                    "archive_path": archive_name,
                    "size_bytes": path.stat().st_size,
                })

            archive.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True),
            )

        return {
            "status": "created",
            "backup": target.name,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "manifest": manifest,
        }

    def list_backups(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.backup_dir.glob("automation-*.zip"), reverse=True):
            items.append({
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            })
        return items

    def get_backup_path(self, name: str) -> Path:
        candidate = (self.backup_dir / Path(name).name).resolve()
        if self.backup_dir.resolve() not in candidate.parents:
            raise ValueError("Invalid backup name.")
        if not candidate.is_file():
            raise FileNotFoundError(name)
        return candidate

    def inspect_backup(self, name: str) -> dict[str, Any]:
        path = self.get_backup_path(name)
        with zipfile.ZipFile(path, "r") as archive:
            if "manifest.json" not in archive.namelist():
                raise ValueError("Backup manifest is missing.")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            return {
                "status": "ok",
                "backup": path.name,
                "manifest": manifest,
                "entries": archive.namelist(),
            }

    def restore_backup(self, name: str, *, create_safety_backup: bool = True) -> dict[str, Any]:
        path = self.get_backup_path(name)
        inspection = self.inspect_backup(name)

        safety = None
        if create_safety_backup:
            safety = self.create_backup("before-restore")

        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            with zipfile.ZipFile(path, "r") as archive:
                archive.extractall(temp_root)

            restored = []
            for source in (temp_root / "data").glob("*.json"):
                destination = self.data_dir / source.name
                payload = json.loads(source.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError(f"Invalid JSON root in {source.name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                restored.append(destination.name)

        return {
            "status": "restored",
            "backup": path.name,
            "restored_files": restored,
            "safety_backup": safety["backup"] if safety else None,
            "manifest": inspection["manifest"],
        }

    def export_configuration(self, label: str | None = None) -> dict[str, Any]:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(
            char if char.isalnum() or char in "-_" else "-"
            for char in (label or "config")
        ).strip("-") or "config"

        target = self.export_dir / f"automation-export-{safe_label}-{stamp}.json"

        payload = {
            "schema_version": 1,
            "exported_at": utc_now(),
            "automation": {},
        }

        for name, path in self.managed_files.items():
            if path.exists():
                payload["automation"][name] = json.loads(
                    path.read_text(encoding="utf-8")
                )

        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return {
            "status": "exported",
            "name": target.name,
            "path": str(target),
            "size_bytes": target.stat().st_size,
        }

    def import_configuration(
        self,
        payload: dict[str, Any],
        *,
        create_safety_backup: bool = True,
    ) -> dict[str, Any]:
        if payload.get("schema_version") != 1:
            raise ValueError("Unsupported export schema version.")

        automation = payload.get("automation")
        if not isinstance(automation, dict):
            raise ValueError("Missing automation configuration object.")

        safety = None
        if create_safety_backup:
            safety = self.create_backup("before-import")

        imported = []

        for name, data in automation.items():
            destination = self.managed_files.get(name)
            if destination is None:
                continue
            if not isinstance(data, dict):
                raise ValueError(f"Invalid configuration for {name}.")

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            imported.append(name)

        return {
            "status": "imported",
            "imported": imported,
            "safety_backup": safety["backup"] if safety else None,
        }


automation_backup_manager = AutomationBackupManager()
