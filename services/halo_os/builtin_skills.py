from __future__ import annotations

from typing import Any

from .contracts import LoadedSkill, SkillManifest


def _offline_tools():
    from services.offline_agent.tool_registry import tool_registry
    from services.offline_agent import tools as _tools  # noqa: F401

    return tool_registry


def _safe_health(tool_name: str) -> dict[str, Any]:
    try:
        registry = _offline_tools()
        result = registry.execute(tool_name, {})

        status = str(result.get("status", "ok")) if isinstance(result, dict) else "ok"
        healthy = status not in {"unavailable", "error", "offline", "stopped"}

        return {
            "status": "healthy" if healthy else "degraded",
            "detail": status,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _tool_skill(
    *,
    name: str,
    title: str,
    description: str,
    tool_name: str,
    intents: tuple[str, ...],
    permissions: tuple[str, ...] = (),
    requires_confirmation: bool = False,
) -> LoadedSkill:
    manifest = SkillManifest(
        name=name,
        title=title,
        version="1.0.0",
        description=description,
        intents=intents,
        permissions=permissions,
        requires_confirmation=requires_confirmation,
        metadata={
            "adapter": "offline_agent",
            "tool": tool_name,
        },
    )

    def execute(arguments: dict[str, Any]) -> dict[str, Any]:
        return _offline_tools().execute(tool_name, arguments)

    def health() -> dict[str, Any]:
        probe = {
            "devices": "list_devices",
            "camera": "camera_status",
            "vision": "vision_status",
            "activity": "activity_summary",
            "automation": "automation_summary",
            "reports": "reports_summary",
            "home": "home_status",
        }.get(name, tool_name)

        return _safe_health(probe)

    return LoadedSkill(
        manifest=manifest,
        execute=execute,
        health=health,
    )


def load_builtin_skills() -> list[LoadedSkill]:
    return [
        _tool_skill(
            name="home",
            title="Home Status",
            description="Unified verified status for the NoorBrain home.",
            tool_name="home_status",
            intents=("home_status", "house_status"),
        ),
        _tool_skill(
            name="devices",
            title="Devices",
            description="List devices and read verified device state.",
            tool_name="list_devices",
            intents=("list_devices", "get_device_status"),
            permissions=("devices.read",),
        ),
        _tool_skill(
            name="camera",
            title="Camera",
            description="Read Raspberry Pi camera connectivity and frame status.",
            tool_name="camera_status",
            intents=("camera_status",),
            permissions=("camera.read",),
        ),
        _tool_skill(
            name="vision",
            title="Vision",
            description="Read person detection and vision-engine health.",
            tool_name="vision_status",
            intents=("vision_status",),
            permissions=("vision.read",),
        ),
        _tool_skill(
            name="activity",
            title="Activity",
            description="Read verified activity and presence summary.",
            tool_name="activity_summary",
            intents=("activity_summary",),
            permissions=("activity.read",),
        ),
        _tool_skill(
            name="automation",
            title="Automation",
            description="Read rules, scenes, routines, and automation diagnostics.",
            tool_name="automation_summary",
            intents=("automation_summary",),
            permissions=("automation.read",),
        ),
        _tool_skill(
            name="reports",
            title="Reports",
            description="Read learning and reporting service health.",
            tool_name="reports_summary",
            intents=("reports_summary",),
            permissions=("reports.read",),
        ),
        _tool_skill(
            name="system",
            title="System Health",
            description="Read verified NoorBrain component health.",
            tool_name="system_health",
            intents=("system_health",),
            permissions=("system.read",),
        ),
    ]
