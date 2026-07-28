from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .store import MemoryStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get(
        "NOORBRAIN_MEMORY_DB",
        str(PROJECT_ROOT / "data" / "ai_memory.db"),
    )
)

store = MemoryStore(DATABASE_PATH)
router = APIRouter(prefix="/api/memory", tags=["AI Memory"])


class MemoryCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    person_id: str | None = Field(default=None, max_length=128)
    zone: str | None = Field(default=None, max_length=128)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="manual", max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: float | None = None


@router.get("/health")
def memory_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ai_memory",
        "database": str(DATABASE_PATH),
        "stats": store.stats(),
    }


@router.post("")
def create_memory(payload: MemoryCreate) -> dict[str, Any]:
    memory = store.add(**payload.model_dump())
    return {"status": "created", "memory": memory}


@router.get("")
def list_memories(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    kind: str | None = None,
    person_id: str | None = None,
    zone: str | None = None,
    query: str | None = None,
    include_expired: bool = False,
) -> dict[str, Any]:
    memories = store.list(
        limit=limit,
        offset=offset,
        kind=kind,
        person_id=person_id,
        zone=zone,
        query=query,
        include_expired=include_expired,
    )
    return {
        "count": len(memories),
        "limit": limit,
        "offset": offset,
        "memories": memories,
    }


@router.get("/stats")
def memory_stats() -> dict[str, Any]:
    return store.stats()


@router.get("/context")
def memory_context(
    person_id: str | None = None,
    zone: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    return store.context(person_id=person_id, zone=zone, limit=limit)


@router.get("/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    try:
        return store.get(memory_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Memory not found") from error


@router.delete("/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, Any]:
    if not store.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "memory_id": memory_id}


@router.post("/maintenance/clear-expired")
def clear_expired_memories() -> dict[str, Any]:
    deleted = store.clear_expired()
    return {"status": "complete", "deleted": deleted}
