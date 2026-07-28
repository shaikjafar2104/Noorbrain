from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from .context_memory import context_memory
from .conversation import conversation_engine
from .registry import skill_registry
from .task_engine import task_engine

router = APIRouter(prefix="/api/halo-os", tags=["HALO OS"])


class ConversationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=120)
    confirm: bool = False


@router.get("/health")
async def health() -> dict[str, Any]:
    result = await asyncio.to_thread(skill_registry.health)
    return {
        "service": "halo_os",
        "version": "3.0-phaseA-complete",
        **result,
    }


@router.get("/skills")
async def skills() -> dict[str, Any]:
    items = await asyncio.to_thread(skill_registry.list)
    return {"status": "ok", "count": len(items), "skills": items}


@router.post("/skills/reload")
async def reload_skills() -> dict[str, Any]:
    return await asyncio.to_thread(skill_registry.reload)


@router.post("/skills/{skill_name}/execute")
async def execute_skill(
    skill_name: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    try:
        result = await asyncio.to_thread(
            skill_registry.execute,
            skill_name,
            payload,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"status": "ok", "skill": skill_name, "result": result}


@router.post("/conversation")
async def conversation(payload: ConversationRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            conversation_engine.process,
            payload.text,
            session_id=payload.session_id,
            confirm=payload.confirm,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/context/sessions")
async def context_sessions() -> dict[str, Any]:
    items = await asyncio.to_thread(context_memory.list_sessions)
    return {"status": "ok", "count": len(items), "sessions": items}


@router.get("/context/{session_id}")
async def get_context(session_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        **await asyncio.to_thread(context_memory.get, session_id),
    }


@router.patch("/context/{session_id}")
async def update_context(
    session_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    item = await asyncio.to_thread(
        context_memory.update,
        session_id,
        payload,
    )
    return {"status": "updated", **item}


@router.put("/context/{session_id}")
async def replace_context(
    session_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    item = await asyncio.to_thread(
        context_memory.replace,
        session_id,
        payload,
    )
    return {"status": "replaced", **item}


@router.delete("/context/{session_id}")
async def clear_context(session_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        context_memory.clear,
        session_id,
    )
    return {
        "status": "deleted",
        "session_id": session_id,
        "removed": removed,
    }


@router.get("/tasks")
async def tasks() -> dict[str, Any]:
    items = await asyncio.to_thread(task_engine.list)
    return {"status": "ok", "count": len(items), "tasks": items}


@router.post("/tasks")
async def create_task(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        task = await asyncio.to_thread(
            task_engine.create,
            str(payload.get("title") or ""),
            list(payload.get("steps") or []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "task": task}


@router.patch("/tasks/{task_id}/status")
async def task_status(
    task_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        task = await asyncio.to_thread(
            task_engine.update_status,
            task_id,
            str(payload.get("status") or "pending"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "task": task}
