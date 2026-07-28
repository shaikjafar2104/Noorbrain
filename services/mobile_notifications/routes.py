from __future__ import annotations

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Query,
)

from .service import mobile_notification_service
from .store import mobile_notification_store

router = APIRouter(
    prefix="/api/mobile-notifications",
    tags=["Mobile Notifications"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    summary = await asyncio.to_thread(
        mobile_notification_store.summary
    )

    return {
        "status": "healthy",
        "service": "mobile_notifications",
        "version": "1.0.0",
        **summary,
    }


@router.get("/settings")
async def settings() -> dict[str, Any]:
    data = await asyncio.to_thread(
        mobile_notification_store.read
    )

    return {
        "status": "ok",
        "settings": data["settings"],
    }


@router.patch("/settings")
async def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    updated = await asyncio.to_thread(
        mobile_notification_store.update_settings,
        payload,
    )

    return {
        "status": "updated",
        "settings": updated,
    }


@router.post("")
async def create_notification(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        mobile_notification_service.publish,
        payload,
    )


@router.get("")
async def notifications(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    category: str | None = None,
    unread_only: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        mobile_notification_store.list,
        limit=limit,
        category=category,
        unread_only=unread_only,
        include_archived=include_archived,
    )

    return {
        "status": "ok",
        "count": len(items),
        "notifications": items,
    }


@router.get("/summary")
async def summary() -> dict[str, Any]:
    return await asyncio.to_thread(
        mobile_notification_store.summary
    )


@router.get("/{notification_id}")
async def notification_detail(
    notification_id: str,
) -> dict[str, Any]:
    item = await asyncio.to_thread(
        mobile_notification_store.get,
        notification_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return {
        "status": "ok",
        "notification": item,
    }


@router.post("/{notification_id}/action")
async def notification_action(
    notification_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            mobile_notification_service.action,
            notification_id=notification_id,
            action=str(payload["action"]),
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


@router.post("/actions/mark-all-read")
async def mark_all_read() -> dict[str, Any]:
    updated = await asyncio.to_thread(
        mobile_notification_store.mark_all_read
    )

    return {
        "status": "updated",
        "updated_count": updated,
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        mobile_notification_store.delete,
        notification_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return {
        "status": "deleted",
        "notification_id": notification_id,
    }


@router.delete("/actions/clear-archived")
async def clear_archived() -> dict[str, Any]:
    removed = await asyncio.to_thread(
        mobile_notification_store.clear_archived
    )

    return {
        "status": "cleared",
        "removed_count": removed,
    }
