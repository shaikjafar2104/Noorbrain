from __future__ import annotations
import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .rule_engine import automation_rule_engine
from .store import automation_store

router = APIRouter(
    prefix="/api/smart-automation",
    tags=["Smart Automation"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    rules = await asyncio.to_thread(
        automation_store.list_rules
    )
    runs = await asyncio.to_thread(
        automation_store.list_runs,
        1,
    )

    return {
        "status": "healthy",
        "service": "smart_automation",
        "version": "4.0-d4.1-d4.2",
        "rule_count": len(rules),
        "run_count": len(runs),
    }


@router.post("/rules")
async def create_rule(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Rule name is required.",
        )

    rule = await asyncio.to_thread(
        automation_store.create_rule,
        {
            "name": name,
            "description": payload.get("description"),
            "condition_mode": payload.get("condition_mode", "all"),
            "conditions": list(payload.get("conditions") or []),
            "schedule": dict(payload.get("schedule") or {"kind": "manual"}),
            "actions": list(payload.get("actions") or []),
            "metadata": dict(payload.get("metadata") or {}),
        },
    )

    return {
        "status": "created",
        "rule": rule,
    }


@router.get("/rules")
async def rules() -> dict[str, Any]:
    items = await asyncio.to_thread(
        automation_store.list_rules
    )

    return {
        "status": "ok",
        "count": len(items),
        "rules": items,
    }


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        rule = await asyncio.to_thread(
            automation_store.update_rule,
            rule_id,
            payload,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Rule not found.",
        ) from exc

    return {
        "status": "updated",
        "rule": rule,
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        automation_store.delete_rule,
        rule_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Rule not found.",
        )

    return {
        "status": "deleted",
        "rule_id": rule_id,
    }


@router.post("/evaluate")
async def evaluate(
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        automation_rule_engine.evaluate_all,
        event_type=payload.get("event_type"),
        person_id=payload.get("person_id"),
        zone=payload.get("zone"),
        metadata=dict(payload.get("metadata") or {}),
        force=bool(payload.get("force", False)),
    )


@router.get("/runs")
async def runs(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        automation_store.list_runs,
        limit,
    )

    return {
        "status": "ok",
        "count": len(items),
        "runs": items,
    }
