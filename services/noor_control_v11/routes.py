from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from services.noor_settings.service import noor_settings
from services.unified_device_runtime import unified_device_runtime


router = APIRouter(
    prefix="/api/noor-control-v11",
    tags=["Noor Control V11"],
)


def _devices() -> list[dict[str, Any]]:
    result = unified_device_runtime.list_devices()

    if isinstance(result, list):
        return result

    if isinstance(result, dict):
        return list(result.get("devices") or [])

    return []


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "noor_control_v11",
        "version": "11.5.0",
        "capabilities": [
            "settings",
            "devices",
            "device_state",
            "rooms",
            "voice_ready",
            "web_ready",
            "android_ready",
        ],
    }


@router.get("/state")
def state() -> dict[str, Any]:
    devices = _devices()

    return {
        "status": "ok",
        "settings": noor_settings.get_all(),
        "devices": devices,
        "device_count": len(devices),
    }


@router.get("/devices")
def devices() -> dict[str, Any]:
    items = _devices()

    return {
        "status": "ok",
        "count": len(items),
        "devices": items,
    }


@router.post("/devices/{device_name}/state")
def device_state(
    device_name: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:

    state = str(
        payload.get("state") or ""
    ).strip().casefold()

    if state not in {
        "on",
        "off",
        "toggle",
    }:
        raise HTTPException(
            422,
            "state must be on, off, or toggle",
        )

    if state == "toggle":
        current = unified_device_runtime.status(
            device_name
        )

        device = current.get("device") or {}

        state = (
            "off"
            if str(device.get("state")).casefold()
            == "on"
            else "on"
        )

    result = unified_device_runtime.set_state(
        device_name,
        state,
    )

    return {
        "status": "ok",
        "control": "device_state",
        "requested_state": state,
        "result": result,
    }


@router.patch("/settings/{section}")
def settings_section(
    section: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:

    try:
        values = noor_settings.update_section(
            section,
            payload,
        )
    except KeyError:
        raise HTTPException(
            404,
            "Unknown settings section",
        )

    return {
        "status": "ok",
        "control": "settings",
        "section": section,
        "settings": values,
    }


@router.post("/command")
def command(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:

    action = str(
        payload.get("action") or ""
    ).strip().casefold()

    if action == "device":
        name = str(
            payload.get("device") or ""
        ).strip()

        target = str(
            payload.get("state") or ""
        ).strip().casefold()

        if not name:
            raise HTTPException(
                422,
                "device is required",
            )

        if target not in {
            "on",
            "off",
            "toggle",
        }:
            raise HTTPException(
                422,
                "state must be on, off, or toggle",
            )

        if target == "toggle":
            current = unified_device_runtime.status(
                name
            )

            device = current.get("device") or {}

            target = (
                "off"
                if str(
                    device.get("state")
                ).casefold() == "on"
                else "on"
            )

        result = unified_device_runtime.set_state(
            name,
            target,
        )

        return {
            "status": "ok",
            "action": "device",
            "device": name,
            "state": target,
            "result": result,
        }

    if action == "settings":
        section = str(
            payload.get("section") or ""
        ).strip()

        values = payload.get("values")

        if not section or not isinstance(
            values,
            dict,
        ):
            raise HTTPException(
                422,
                "section and values are required",
            )

        try:
            updated = noor_settings.update_section(
                section,
                values,
            )
        except KeyError:
            raise HTTPException(
                404,
                "Unknown settings section",
            )

        return {
            "status": "ok",
            "action": "settings",
            "section": section,
            "settings": updated,
        }

    raise HTTPException(
        422,
        "Unknown Noor control action",
    )
