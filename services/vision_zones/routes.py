from __future__ import annotations

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from .models import (
    MotionSample,
    ZoneCreate,
    ZoneUpdate,
)
from .service import vision_zone_service
from .store import zone_store

from services.zone_engine import zone_engine
from services.reminder_rules.reminder_rules import (
    reminder_rules,
)


router = APIRouter(
    prefix="/api/vision-zones",
    tags=["Vision Zones"],
)


def _clean_name(value: str) -> str:
    name=str(value or "").strip()

    if not name:
        raise ValueError(
            "Zone name is required."
        )

    return name


def _find_zone(zone_id: str):
    return next(
        (
            z
            for z in zone_store.list_zones()
            if z.get("id") == zone_id
        ),
        None
    )


def _duplicate_name(
    name: str,
    exclude_id: str | None = None
):
    target=name.casefold()

    for zone in zone_store.list_zones():
        if zone.get("id") == exclude_id:
            continue

        if str(
            zone.get("name") or ""
        ).strip().casefold() == target:
            return True

    return False


def _sync_legacy():
    """
    New Vision Zone store is canonical.

    Legacy camera engine requires:
    name,x1,y1,x2,y2.

    Polygon points are converted to
    bounding rectangles.
    """

    legacy=[]

    for zone in zone_store.list_zones():

        if not zone.get("enabled",True):
            continue

        points=zone.get("points") or []

        if len(points) < 3:
            continue

        meta=zone.get("metadata") or {}

        width=int(
            meta.get("frame_width")
            or 1280
        )

        height=int(
            meta.get("frame_height")
            or 720
        )

        xs=[
            float(p["x"])
            for p in points
        ]

        ys=[
            float(p["y"])
            for p in points
        ]

        legacy.append({
            "name":zone["name"],
            "x1":round(min(xs)*width),
            "y1":round(min(ys)*height),
            "x2":round(max(xs)*width),
            "y2":round(max(ys)*height),
        })

    zone_engine.save_zones(legacy)

    return legacy


def _rename_rules(
    old_name: str,
    new_name: str
):
    changed=[]

    for rule in reminder_rules.list_rules():

        if rule.get("zone") != old_name:
            continue

        patch={
            "zone":new_name
        }

        old_rule_name=str(
            rule.get("name") or ""
        )

        # Keep human-readable rule names
        # synchronized when they start
        # with the old zone name.
        if old_rule_name.startswith(
            old_name
        ):
            patch["name"] = (
                new_name
                + old_rule_name[
                    len(old_name):
                ]
            )

        updated=reminder_rules.update_rule(
            rule["id"],
            patch
        )

        changed.append(updated)

    return changed


def _linked_rules(zone_name: str):
    return [
        r
        for r in reminder_rules.list_rules()
        if r.get("zone") == zone_name
    ]


@router.get("/health")
async def health() -> dict[str,Any]:
    zones=await asyncio.to_thread(
        zone_store.list_zones
    )

    events=await asyncio.to_thread(
        zone_store.list_motion_events,
        limit=1
    )

    return {
        "status":"healthy",
        "service":"vision_zones",
        "version":"12.5-d4",
        "zone_count":len(zones),
        "motion_event_count":len(events),
    }


@router.get("/zones")
async def zones() -> dict[str,Any]:
    items=await asyncio.to_thread(
        zone_store.list_zones
    )

    return {
        "status":"ok",
        "count":len(items),
        "zones":items,
    }


@router.post("/zones")
async def create_zone(
    payload: ZoneCreate
) -> dict[str,Any]:

    data=payload.model_dump(
        mode="json"
    )

    try:
        data["name"]=_clean_name(
            data["name"]
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    if _duplicate_name(data["name"]):
        raise HTTPException(
            status_code=409,
            detail="Zone name already exists."
        )

    metadata=dict(
        data.get("metadata") or {}
    )

    metadata.setdefault(
        "frame_width",
        1280
    )

    metadata.setdefault(
        "frame_height",
        720
    )

    metadata.setdefault(
        "source",
        "custom-zone-manager-v12.5"
    )

    data["metadata"]=metadata

    item=await asyncio.to_thread(
        zone_store.save_zone,
        data
    )

    try:
        legacy=await asyncio.to_thread(
            _sync_legacy
        )
    except Exception:
        await asyncio.to_thread(
            zone_store.delete_zone,
            item["id"]
        )
        raise

    return {
        "status":"created",
        "zone":item,
        "legacy_count":len(legacy),
    }


@router.put("/zones/{zone_id}")
async def update_zone(
    zone_id: str,
    payload: ZoneUpdate
) -> dict[str,Any]:

    existing=_find_zone(zone_id)

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="Zone not found."
        )

    patch=payload.model_dump(
        mode="json",
        exclude_none=True
    )

    old_name=existing["name"]

    if "name" in patch:
        try:
            patch["name"]=_clean_name(
                patch["name"]
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        if _duplicate_name(
            patch["name"],
            zone_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Zone name already exists."
                )
            )

    merged=dict(existing)
    merged.update(patch)
    merged["id"]=existing["id"]
    merged["created_at"]=existing.get(
        "created_at"
    )

    saved=await asyncio.to_thread(
        zone_store.save_zone,
        merged
    )

    new_name=saved["name"]

    changed_rules=[]

    try:
        if new_name != old_name:
            changed_rules=await asyncio.to_thread(
                _rename_rules,
                old_name,
                new_name
            )

        legacy=await asyncio.to_thread(
            _sync_legacy
        )

    except Exception:
        # Restore zone.
        await asyncio.to_thread(
            zone_store.save_zone,
            existing
        )

        # Restore any renamed rules.
        if new_name != old_name:
            await asyncio.to_thread(
                _rename_rules,
                new_name,
                old_name
            )

        await asyncio.to_thread(
            _sync_legacy
        )

        raise

    return {
        "status":"updated",
        "zone":saved,
        "renamed_rules":len(
            changed_rules
        ),
        "legacy_count":len(legacy),
    }


@router.delete("/zones/{zone_id}")
async def delete_zone(
    zone_id: str,
    force: bool = Query(default=False)
) -> dict[str,Any]:

    existing=_find_zone(zone_id)

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="Zone not found."
        )

    linked=_linked_rules(
        existing["name"]
    )

    if linked and not force:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Zone has linked reminder rules.",

                "zone":
                    existing["name"],

                "linked_rules":[
                    {
                        "id":r.get("id"),
                        "name":r.get("name")
                    }
                    for r in linked
                ]
            }
        )

    removed=await asyncio.to_thread(
        zone_store.delete_zone,
        zone_id
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Zone not found."
        )

    try:
        legacy=await asyncio.to_thread(
            _sync_legacy
        )
    except Exception:
        await asyncio.to_thread(
            zone_store.save_zone,
            existing
        )

        await asyncio.to_thread(
            _sync_legacy
        )

        raise

    return {
        "status":"deleted",
        "zone_id":zone_id,
        "zone_name":existing["name"],
        "legacy_count":len(legacy),
    }


@router.post("/sync")
async def sync_zones():
    legacy=await asyncio.to_thread(
        _sync_legacy
    )

    return {
        "status":"synced",
        "count":len(legacy),
        "zones":legacy,
    }


@router.post("/motion")
async def record_motion(
    payload: MotionSample
) -> dict[str,Any]:

    return await asyncio.to_thread(
        vision_zone_service.record_motion,
        camera_id=payload.camera_id,
        x=payload.x,
        y=payload.y,
        confidence=payload.confidence,
        source=payload.source,
        metadata=payload.metadata,
    )


@router.get("/motion")
async def motion_events(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),
    zone_id: str | None = None,
) -> dict[str,Any]:

    items=await asyncio.to_thread(
        zone_store.list_motion_events,
        limit=limit,
        zone_id=zone_id,
    )

    return {
        "status":"ok",
        "count":len(items),
        "events":items,
    }


@router.post("/motion/clear")
async def clear_motion():
    removed=await asyncio.to_thread(
        zone_store.clear_motion_events
    )

    return {
        "status":"cleared",
        "removed":removed,
    }
