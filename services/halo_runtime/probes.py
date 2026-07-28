from __future__ import annotations

from typing import Any

from .component_registry import component_registry


def halo_os_probe() -> dict[str, Any]:
    from services.halo_os.registry import skill_registry

    result = skill_registry.health()
    return {
        "status": result.get("status", "healthy"),
        "skill_count": result.get("skill_count", 0),
        "unavailable": result.get("unavailable", []),
        "degraded": result.get("degraded", []),
    }


def voice_os_probe() -> dict[str, Any]:
    try:
        from services.voice_os.live_pipeline import live_voice_pipeline
        pipeline = live_voice_pipeline.status()
    except Exception as exc:
        pipeline = {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        from services.voice_os.offline_stt import offline_stt
        stt = offline_stt.health()
    except Exception as exc:
        stt = {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        from services.voice_os.offline_tts import offline_tts
        tts = offline_tts.health()
    except Exception as exc:
        tts = {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }

    states = {
        str(pipeline.get("status", "")),
        str(stt.get("status", "")),
        str(tts.get("status", "")),
    }

    status = "healthy"
    if "error" in states or "unavailable" in states:
        status = "degraded"

    return {
        "status": status,
        "pipeline": pipeline,
        "stt": stt,
        "tts": tts,
    }


def offline_agent_probe() -> dict[str, Any]:
    from services.offline_agent.tool_registry import tool_registry
    from services.offline_agent import tools as _tools  # noqa: F401

    names = tool_registry.names()
    return {
        "status": "healthy",
        "tool_count": len(names),
        "tools": names,
    }


def automation_probe() -> dict[str, Any]:
    from services.automation.diagnostics import automation_diagnostics

    result = automation_diagnostics.snapshot()
    return {
        "status": result.get("status", "healthy"),
        "counts": result.get("counts", {}),
    }


def activity_probe() -> dict[str, Any]:
    from services.activity_engine import activity_engine

    if not hasattr(activity_engine, "snapshot"):
        return {
            "status": "degraded",
            "reason": "Activity engine snapshot method unavailable.",
        }

    try:
        result = activity_engine.snapshot()
    except TypeError:
        result = activity_engine.snapshot(None)

    if not isinstance(result, dict):
        result = {"value": result}

    return {
        "status": result.get("status", "healthy"),
        "snapshot": result,
    }


def vision_probe() -> dict[str, Any]:
    from services.vision_engine import vision_engine

    result = vision_engine.snapshot()
    if not isinstance(result, dict):
        result = {"value": result}

    return {
        "status": result.get("status", "healthy"),
        "snapshot": result,
    }


def register_builtin_probes() -> None:
    component_registry.register("halo_os", halo_os_probe)
    component_registry.register("voice_os", voice_os_probe)
    component_registry.register("offline_agent", offline_agent_probe)
    component_registry.register("automation", automation_probe)
    component_registry.register("activity", activity_probe)
    component_registry.register("vision", vision_probe)


register_builtin_probes()
