from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .action_executor import automation_action_executor
from .analytics import automation_analytics
from .orchestrator import automation_orchestrator
from .store import automation_store

router = APIRouter(
    prefix="/api/smart-automation",
    tags=["Smart Automation Execution"],
)


@router.post("/execute")
async def execute(
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        automation_orchestrator.evaluate_and_execute,
        event_type=payload.get("event_type"),
        person_id=payload.get("person_id"),
        zone=payload.get("zone"),
        metadata=dict(payload.get("metadata") or {}),
        force=bool(payload.get("force", False)),
        confirmed=bool(payload.get("confirmed", False)),
    )


@router.post("/rules/{rule_id}/run")
async def run_rule(
    rule_id: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    rule = await asyncio.to_thread(
        automation_store.get_rule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail="Rule not found.",
        )

    context = {
        "event_type": payload.get("event_type"),
        "person_id": payload.get("person_id"),
        "zone": payload.get("zone"),
        "metadata": dict(payload.get("metadata") or {}),
    }

    return await asyncio.to_thread(
        automation_action_executor.execute_actions,
        rule=rule,
        context=context,
        confirmed=bool(payload.get("confirmed", False)),
    )


@router.get("/analytics")
async def analytics() -> dict[str, Any]:
    return await asyncio.to_thread(
        automation_analytics.summary
    )


@router.get("/runs/{run_id}")
async def run_detail(run_id: str) -> dict[str, Any]:
    runs = await asyncio.to_thread(
        automation_store.list_runs,
        5000,
    )

    run = next(
        (
            item
            for item in runs
            if item.get("id") == run_id
        ),
        None,
    )

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found.",
        )

    return {
        "status": "ok",
        "run": run,
    }
