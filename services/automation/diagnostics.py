from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"


def read_json_summary(path: Path, list_key: str) -> dict[str, Any]:
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "readable": False,
        "count": 0,
        "size_bytes": 0,
        "error": None,
    }

    if not path.is_file():
        return result

    try:
        result["size_bytes"] = path.stat().st_size

        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        items = payload.get(list_key, [])
        if not isinstance(items, list):
            raise ValueError(
                f"Expected '{list_key}' to be a list."
            )

        result["readable"] = True
        result["count"] = len(items)

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


def package_available(package_name: str) -> bool:
    try:
        return importlib.util.find_spec(
            package_name
        ) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


class AutomationDiagnostics:
    """
    Fast diagnostics only.

    No MQTT connection, hardware scan, network call,
    device probing or shared service lock is performed.
    """

    def snapshot(self) -> dict[str, Any]:
        storage = {
            "devices": read_json_summary(
                DATA_ROOT / "devices.json",
                "devices",
            ),
            "esp32": read_json_summary(
                DATA_ROOT / "esp32_devices.json",
                "devices",
            ),
            "rules": read_json_summary(
                DATA_ROOT / "automation_rules.json",
                "rules",
            ),
            "scenes": read_json_summary(
                DATA_ROOT / "automation_scenes.json",
                "scenes",
            ),
            "groups": read_json_summary(
                DATA_ROOT / "device_groups.json",
                "groups",
            ),
            "routines": read_json_summary(
                DATA_ROOT / "automation_routines.json",
                "routines",
            ),
        }

        required_names = (
            "devices",
            "rules",
            "scenes",
            "groups",
            "routines",
        )

        required_ok = all(
            storage[name]["readable"]
            for name in required_names
        )

        return {
            "status": (
                "healthy"
                if required_ok
                else "degraded"
            ),
            "service": "automation",
            "mode": "non_blocking",
            "checks": {
                "device_storage": storage[
                    "devices"
                ]["readable"],
                "rule_storage": storage[
                    "rules"
                ]["readable"],
                "scene_storage": storage[
                    "scenes"
                ]["readable"],
                "group_storage": storage[
                    "groups"
                ]["readable"],
                "routine_storage": storage[
                    "routines"
                ]["readable"],
                "esp32_storage": storage[
                    "esp32"
                ]["readable"],
                "paho_mqtt_installed": (
                    package_available("paho")
                ),
            },
            "counts": {
                name: details["count"]
                for name, details in storage.items()
            },
            "storage": storage,
            "mqtt": {
                "package_installed": (
                    package_available("paho")
                ),
                "connection_probe": "deferred",
                "hardware_probe": "disabled",
            },
        }


automation_diagnostics = AutomationDiagnostics()
