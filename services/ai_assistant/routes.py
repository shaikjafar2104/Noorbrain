from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.ai_memory.store import MemoryStore
from .assistant import LocalAssistant

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get("NOORBRAIN_MEMORY_DB", str(PROJECT_ROOT / "data" / "ai_memory.db"))
)

store = MemoryStore(DATABASE_PATH)
assistant = LocalAssistant(store)
router = APIRouter(prefix="/api/ai", tags=["Sprint 7 AI Assistant"])


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=50)


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ai_assistant",
        "mode": "offline-local",
        "database": str(DATABASE_PATH),
        "time": time.time(),
    }


@router.get("/search")
def natural_language_search(
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    return assistant.search(q, limit=limit)


@router.post("/ask")
def ask(payload: AssistantRequest) -> dict[str, Any]:
    return assistant.answer(payload.message, limit=payload.limit)


@router.get("/insights")
def insights(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    return assistant.insights(limit=limit)


@router.post("/maintenance/optimize")
def optimize() -> dict[str, Any]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DATABASE_PATH), timeout=30) as connection:
        connection.execute("PRAGMA optimize")
        connection.execute("ANALYZE")
        connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
    return {"status": "optimized", "database": str(DATABASE_PATH)}


@router.get("/release")
def release() -> dict[str, Any]:
    return {
        "name": "NoorBrain Sprint 7",
        "version": "7.0-rc1",
        "components": [
            "AI Memory Engine",
            "Person Intelligence",
            "Habit Learning",
            "Daily Timeline",
            "Reminder Intelligence",
            "Natural Language Memory Search",
            "Local AI Assistant",
            "AI Insights Dashboard",
            "Database Optimization",
        ],
        "cloud_required": False,
    }
