from __future__ import annotations

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
)

from .acknowledgements import (
    notification_acknowledgement_service,
)
from .dnd import notification_dnd_service
from .final_service import (
    mobile_notification_final_service,
)

router = APIRouter(
    prefix="/api/mobile-notifications",
    tags=["Mobile Notifications Final"],
)


@router.get("/system-status")
async def system_status() -> dict[str, Any]:
    return await asyncio.to_thread(
        mobile_notification_final_service.system_status
    )


@router.get("/dnd/status")
async def dnd_status() -> dict[str, Any]:
    return await asyncio.to_thread(
        notification_dnd_service.status
    )


@router.post("/{notification_id}/acknowledge")
async def acknowledge(
    notification_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            notification_acknowledgement_service.acknowledge,
            notification_id=notification_id,
            action=str(payload["action"]),
            snooze_minutes=int(
                payload.get("snooze_minutes", 10)
            ),
            note=payload.get("note"),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/snoozed/reactivate")
async def reactivate_snoozed() -> dict[str, Any]:
    return await asyncio.to_thread(
        notification_acknowledgement_service.due_snoozed
    )


@router.post("/publish-final")
async def publish_final(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        mobile_notification_final_service.publish,
        payload,
    )
