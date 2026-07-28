from __future__ import annotations

from typing import Any, Callable

from services.automation.models import DeviceState

from .cache import agent_cache
from .tool_registry import tool_registry


def _device_manager():
    from services.automation.manager import device_manager
    return device_manager


def _scene_manager():
    from services.automation.scene_manager import scene_manager
    return scene_manager


def _routine_scheduler():
    from services.automation.routine_scheduler import routine_scheduler
    return routine_scheduler


def _automation_diagnostics():
    from services.automation.diagnostics import automation_diagnostics
    return automation_diagnostics


def _safe_call(name: str, producer: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        result = producer()
        if not isinstance(result, dict):
            return {"status": "degraded", "service": name, "detail": str(result)}
        return result
    except Exception as exc:
        return {
            "status": "unavailable",
            "service": name,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _device_snapshot() -> list[Any]:
    return agent_cache.get_or_set(
        "devices:list",
        2.0,
        lambda: _device_manager().list_devices(),
    )


def _find_device_by_name(name: str):
    normalized = name.strip().casefold()
    devices = _device_snapshot()

    exact = next(
        (item for item in devices if item.name.casefold() == normalized),
        None,
    )
    if exact is not None:
        return exact

    partial = [
        item for item in devices
        if normalized in item.name.casefold()
        or item.name.casefold() in normalized
    ]
    return partial[0] if len(partial) == 1 else None


def list_devices(arguments: dict[str, Any]) -> dict[str, Any]:
    devices = _device_snapshot()
    return {
        "status": "ok",
        "count": len(devices),
        "devices": [item.model_dump(mode="json") for item in devices],
        "cached_for_seconds": 2,
    }


def get_device_status(arguments: dict[str, Any]) -> dict[str, Any]:
    name = str(arguments.get("name") or "").strip()
    if not name:
        raise ValueError("Device name is required.")

    device = _find_device_by_name(name)
    if device is None:
        return {"status": "not_found", "query": name}

    return {
        "status": "ok",
        "device": device.model_dump(mode="json"),
    }


def set_device_state(arguments: dict[str, Any]) -> dict[str, Any]:
    name = str(arguments.get("name") or "").strip()
    state = str(arguments.get("state") or "").strip().lower()

    if not name:
        raise ValueError("Device name is required.")
    if state not in {"on", "off"}:
        raise ValueError("State must be on or off.")

    device = _find_device_by_name(name)
    if device is None:
        return {"status": "not_found", "query": name}

    enum_state = DeviceState.ON if state == "on" else DeviceState.OFF
    updated = _device_manager().set_state(device.id, enum_state)
    agent_cache.clear("devices:")
    agent_cache.clear("home:")

    return {
        "status": "ok",
        "device": updated.model_dump(mode="json"),
    }


def list_scenes(arguments: dict[str, Any]) -> dict[str, Any]:
    scenes = agent_cache.get_or_set(
        "scenes:list",
        3.0,
        lambda: _scene_manager().list(),
    )
    return {"status": "ok", "count": len(scenes), "scenes": scenes}


def run_scene(arguments: dict[str, Any]) -> dict[str, Any]:
    name = str(arguments.get("name") or "").strip().casefold()
    scenes = agent_cache.get_or_set(
        "scenes:list",
        3.0,
        lambda: _scene_manager().list(),
    )
    scene = next(
        (item for item in scenes if str(item.get("name", "")).casefold() == name),
        None,
    )

    if scene is None:
        return {"status": "not_found", "query": name}

    result = _scene_manager().execute(scene["id"])
    agent_cache.clear("devices:")
    agent_cache.clear("home:")
    return result


def list_routines(arguments: dict[str, Any]) -> dict[str, Any]:
    routines = agent_cache.get_or_set(
        "routines:list",
        3.0,
        lambda: _routine_scheduler().list(),
    )
    return {"status": "ok", "count": len(routines), "routines": routines}


def automation_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    return agent_cache.get_or_set(
        "automation:summary",
        3.0,
        lambda: _automation_diagnostics().snapshot(),
    )


def camera_status(arguments: dict[str, Any]) -> dict[str, Any]:
    def build() -> dict[str, Any]:
        from services.camera_client import camera_client
        snapshot = camera_client.snapshot()
        return {"status": "online" if snapshot.get("connected") else "offline", **snapshot}

    return agent_cache.get_or_set(
        "home:camera",
        2.0,
        lambda: _safe_call("camera", build),
    )


def vision_status(arguments: dict[str, Any]) -> dict[str, Any]:
    def build() -> dict[str, Any]:
        from services.vision_engine import vision_engine
        snapshot = vision_engine.snapshot()
        return {"status": "running" if snapshot.get("running") else "stopped", **snapshot}

    return agent_cache.get_or_set(
        "home:vision",
        2.0,
        lambda: _safe_call("vision", build),
    )


def activity_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    def build() -> dict[str, Any]:
        from services.activity_engine import activity_engine
        snapshot = activity_engine.snapshot(limit=20)
        return {"status": snapshot.get("status", "running"), **snapshot}

    return agent_cache.get_or_set(
        "home:activity",
        2.0,
        lambda: _safe_call("activity", build),
    )


def reports_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    def build() -> dict[str, Any]:
        from services.learning.storage import get_store
        from services.reports.storage import get_report_store

        learning = get_store()
        reports = get_report_store()
        return {
            "status": "healthy",
            "learning_events": learning.count_events(),
            "learning_integrity": learning.integrity_check(),
            "report_integrity": reports.integrity_check(),
        }

    return agent_cache.get_or_set(
        "home:reports",
        10.0,
        lambda: _safe_call("reports", build),
    )


def system_health(arguments: dict[str, Any]) -> dict[str, Any]:
    components = {
        "camera": camera_status({}),
        "vision": vision_status({}),
        "activity": activity_summary({}),
        "automation": automation_summary({}),
        "reports": reports_summary({}),
    }

    unavailable = [
        name for name, payload in components.items()
        if payload.get("status") in {"unavailable", "offline", "stopped"}
    ]

    return {
        "status": "healthy" if not unavailable else "degraded",
        "unavailable": unavailable,
        "components": components,
    }


def home_status(arguments: dict[str, Any]) -> dict[str, Any]:
    def build() -> dict[str, Any]:
        devices = list_devices({})
        health = system_health({})
        camera = health["components"]["camera"]
        vision = health["components"]["vision"]
        activity = health["components"]["activity"]
        automation = health["components"]["automation"]
        reports = health["components"]["reports"]

        return {
            "status": health["status"],
            "devices": devices,
            "camera": camera,
            "vision": vision,
            "activity": activity,
            "automation": automation,
            "reports": reports,
            "alerts": health["unavailable"],
        }

    return agent_cache.get_or_set(
        "home:summary",
        3.0,
        lambda: _safe_call("home", build),
    )


def skills_status(arguments: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "devices": lambda: list_devices({}),
        "camera": lambda: camera_status({}),
        "vision": lambda: vision_status({}),
        "activity": lambda: activity_summary({}),
        "automation": lambda: automation_summary({}),
        "reports": lambda: reports_summary({}),
    }

    skills = []
    for name, producer in checks.items():
        result = _safe_call(name, producer)
        raw_status = str(result.get("status", "unknown"))
        available = raw_status not in {"unavailable"}
        skills.append({
            "name": name,
            "available": available,
            "status": raw_status,
        })

    skills.extend([
        {"name": "scenes", "available": True, "status": "ready"},
        {"name": "routines", "available": True, "status": "ready"},
        {"name": "local_ai", "available": True, "status": "ready"},
    ])

    return {
        "status": "ok",
        "count": len(skills),
        "skills": skills,
    }


tool_registry.register("list_devices", list_devices)
tool_registry.register("get_device_status", get_device_status)
tool_registry.register(
    "set_device_state",
    set_device_state,
    requires_confirmation=True,
)
tool_registry.register("list_scenes", list_scenes)
tool_registry.register(
    "run_scene",
    run_scene,
    requires_confirmation=True,
)
tool_registry.register("list_routines", list_routines)
tool_registry.register("automation_summary", automation_summary)
tool_registry.register("camera_status", camera_status)
tool_registry.register("vision_status", vision_status)
tool_registry.register("activity_summary", activity_summary)
tool_registry.register("reports_summary", reports_summary)
tool_registry.register("system_health", system_health)
tool_registry.register("home_status", home_status)
tool_registry.register("skills_status", skills_status)
