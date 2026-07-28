from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from .executor import action_plan_executor
from .models import PlanRequest
from .planner import multi_turn_planner
from .store import plan_store

router = APIRouter(
    prefix="/api/halo-action-planner",
    tags=["HALO Action Planner"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_action_planner",
        "version": "3.2-c2.4-c2.5",
        "plan_count": len(plan_store.list()),
    }


@router.post("/plan")
async def create_plan(payload: PlanRequest) -> dict[str, Any]:
    context = {}

    try:
        from services.halo_conversation.session_manager import conversation_sessions
        session = conversation_sessions.get(payload.session_id)
        context = dict(session.get("context") or {})
    except Exception:
        pass

    plan = await asyncio.to_thread(
        multi_turn_planner.plan,
        payload.text,
        context,
    )
    saved = await asyncio.to_thread(plan_store.save, plan)

    return {
        "status": "planned",
        "plan": saved,
    }


@router.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    plan = await asyncio.to_thread(plan_store.get, plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")

    execution = await asyncio.to_thread(
        action_plan_executor.execute,
        plan,
        confirmed=confirmed,
    )

    saved = await asyncio.to_thread(
        plan_store.update_execution,
        plan_id,
        execution,
    )

    return {
        "status": execution["status"],
        "plan": saved,
        "execution": execution,
    }


@router.get("/plans")
async def plans() -> dict[str, Any]:
    items = await asyncio.to_thread(plan_store.list)
    return {
        "status": "ok",
        "count": len(items),
        "plans": items,
    }


@router.get("/plans/{plan_id}")
async def plan(plan_id: str) -> dict[str, Any]:
    item = await asyncio.to_thread(plan_store.get, plan_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "status": "ok",
        "plan": item,
    }
