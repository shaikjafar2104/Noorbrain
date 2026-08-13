from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .service import noor_settings
from .runtime import apply_runtime_settings, runtime_snapshot


router = APIRouter(
    prefix="/api/noor-settings-v11",
    tags=["Noor Settings V11"],
)


@router.get("/health")
def health() -> dict[str, Any]:
    settings = noor_settings.get_all()

    return {
        "status": "healthy",
        "service": "noor_settings",
        "version": "11.1.0",
        "sections": sorted(settings.keys()),
    }


@router.get("")
def get_settings() -> dict[str, Any]:
    return {
        "status": "ok",
        "settings": noor_settings.get_all(),
    }


@router.get("/{section}")
def get_section(
    section: str,
) -> dict[str, Any]:
    try:
        values = noor_settings.get_section(section)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Unknown settings section",
        )

    return {
        "status": "ok",
        "section": section,
        "settings": values,
    }


@router.patch("/{section}")
def update_section(
    section: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        values = noor_settings.update_section(
            section,
            payload,
        )
        runtime = apply_runtime_settings()
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Unknown settings section",
        )

    return {
        "status": "ok",
        "section": section,
        "settings": values,
        "runtime": runtime,
    }


@router.patch("")
def update_all(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    settings = noor_settings.update_all(payload)
    runtime = apply_runtime_settings()

    return {
        "status": "ok",
        "settings": settings,
        "runtime": runtime,
    }


@router.post("/reset/defaults")
def reset_defaults() -> dict[str, Any]:
    settings = noor_settings.reset()
    runtime = apply_runtime_settings()

    return {
        "status": "ok",
        "settings": settings,
        "runtime": runtime,
    }


@router.get("/runtime/status")
def runtime_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "runtime": runtime_snapshot(),
    }


@router.post("/runtime/apply")
def runtime_apply() -> dict[str, Any]:
    return {
        "status": "ok",
        "runtime": apply_runtime_settings(),
    }
