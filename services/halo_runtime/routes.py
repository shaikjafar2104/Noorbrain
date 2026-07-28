from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body

from .component_registry import component_registry
from .config_store import runtime_config_store
from .models import RuntimeActionRequest
from .runtime import halo_runtime_manager

router = APIRouter(prefix="/api/halo-runtime", tags=["HALO Runtime"])


@router.get("/health")
async def health() -> dict[str, Any]:
    status = halo_runtime_manager.status()
    return {
        **status,
        "healthy": status["runtime_state"] not in {"error"},
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    return halo_runtime_manager.status()


@router.post("/start")
async def start(
    payload: RuntimeActionRequest = RuntimeActionRequest(),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_runtime_manager.start,
        payload.reason,
    )


@router.post("/stop")
async def stop(
    payload: RuntimeActionRequest = RuntimeActionRequest(),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_runtime_manager.stop,
        payload.reason,
    )


@router.post("/restart")
async def restart(
    payload: RuntimeActionRequest = RuntimeActionRequest(),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_runtime_manager.restart,
        payload.reason,
    )


@router.post("/heartbeat")
async def heartbeat() -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_runtime_manager.heartbeat,
    )


@router.get("/components")
async def components() -> dict[str, Any]:
    items = await asyncio.to_thread(
        component_registry.inspect_all,
    )

    return {
        "status": "ok",
        "count": len(items),
        "components": [
            item.model_dump(mode="json")
            for item in items
        ],
    }


@router.get("/config")
async def get_config() -> dict[str, Any]:
    return {
        "status": "ok",
        "config": runtime_config_store.read().model_dump(mode="json"),
    }


@router.patch("/config")
async def update_config(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    config = await asyncio.to_thread(
        runtime_config_store.update,
        payload,
    )

    return {
        "status": "updated",
        "config": config.model_dump(mode="json"),
    }
