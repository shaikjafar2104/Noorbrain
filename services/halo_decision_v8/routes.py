from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(
    prefix="/api/halo-decision-v8",
    tags=["HALO Decision v8"],
)

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "halo_decision_v8.json"

DEFAULT: dict[str, Any] = {
    "version": 1,
    "queue": [],
    "history": [],
    "context": {
        "presence": 0.0,
        "vision": 0.0,
        "prayer": 0.0,
        "habit": 0.0,
        "urgency": 0.0,
        "time_relevance": 0.0,
    },
    "settings": {
        "enabled": True,
        "minimum_score": 0.55,
        "max_queue": 50,
        "auto_expire_seconds": 1800,
    },
}


def read_store() -> dict[str, Any]:
    STORE.parent.mkdir(parents=True, exist_ok=True)

    if not STORE.exists():
        write_store(DEFAULT.copy())
        return json.loads(json.dumps(DEFAULT))

    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = json.loads(json.dumps(DEFAULT))

    if isinstance(data, dict):
        result.update(data)

    result.setdefault("queue", [])
    result.setdefault("history", [])
    result.setdefault("context", DEFAULT["context"].copy())
    result.setdefault("settings", DEFAULT["settings"].copy())
    return result


def write_store(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    temp = STORE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STORE)


def clamp(value: Any) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = 0.0

    return max(0.0, min(1.0, numeric))


def score_context(context: dict[str, Any]) -> dict[str, Any]:
    weights = {
        "presence": 0.18,
        "vision": 0.15,
        "prayer": 0.18,
        "habit": 0.15,
        "urgency": 0.24,
        "time_relevance": 0.10,
    }

    normalized = {
        key: clamp(context.get(key, 0.0))
        for key in weights
    }

    total = sum(
        normalized[key] * weight
        for key, weight in weights.items()
    )

    return {
        "score": round(total, 4),
        "normalized": normalized,
        "weights": weights,
    }


def prune(data: dict[str, Any]) -> None:
    now = int(time.time())
    expiry = int(data["settings"].get("auto_expire_seconds", 1800))

    active = []

    for item in data["queue"]:
        created = int(item.get("created_at", now))
        expired = now - created > expiry

        if expired:
            item["status"] = "expired"
            item["resolved_at"] = now
            data["history"].append(item)
        else:
            active.append(item)

    data["queue"] = active
    data["history"] = data["history"][-500:]


def sort_queue(data: dict[str, Any]) -> None:
    data["queue"].sort(
        key=lambda item: (
            float(item.get("priority_score", 0)),
            int(item.get("created_at", 0)),
        ),
        reverse=True,
    )

    max_queue = int(data["settings"].get("max_queue", 50))
    overflow = data["queue"][max_queue:]

    for item in overflow:
        item["status"] = "overflow"
        item["resolved_at"] = int(time.time())
        data["history"].append(item)

    data["queue"] = data["queue"][:max_queue]


@router.get("/health")
def health() -> dict[str, Any]:
    data = read_store()
    prune(data)
    write_store(data)

    return {
        "status": "healthy",
        "service": "halo_decision_v8",
        "version": "8.1.0",
        "queue_size": len(data["queue"]),
        "history_size": len(data["history"]),
        "enabled": bool(data["settings"].get("enabled", True)),
    }


@router.get("/state")
def state() -> dict[str, Any]:
    data = read_store()
    prune(data)
    sort_queue(data)
    write_store(data)

    return {
        "status": "ok",
        "decision_engine": data,
        "top_decision": data["queue"][0] if data["queue"] else None,
    }


@router.post("/score")
def score(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    context = payload.get("context") or payload
    result = score_context(context)

    return {
        "status": "ok",
        **result,
    }


@router.post("/context")
def update_context(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_store()

    for key in DEFAULT["context"]:
        if key in payload:
            data["context"][key] = clamp(payload[key])

    scored = score_context(data["context"])
    write_store(data)

    return {
        "status": "updated",
        "context": data["context"],
        "score": scored["score"],
    }


@router.post("/decisions")
def add_decision(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    action = str(payload.get("action") or "").strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Decision title is required.",
        )

    if not action:
        raise HTTPException(
            status_code=422,
            detail="Decision action is required.",
        )

    data = read_store()

    if not data["settings"].get("enabled", True):
        raise HTTPException(
            status_code=409,
            detail="Decision engine is disabled.",
        )

    context = {
        **data["context"],
        **(payload.get("context") or {}),
    }

    scored = score_context(context)
    manual_priority = clamp(payload.get("manual_priority", 0.0))
    priority_score = round(
        min(1.0, scored["score"] * 0.8 + manual_priority * 0.2),
        4,
    )

    minimum = float(
        data["settings"].get("minimum_score", 0.55)
    )

    decision = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "action": action,
        "source": str(payload.get("source") or "halo"),
        "category": str(payload.get("category") or "general"),
        "message": str(payload.get("message") or ""),
        "context": scored["normalized"],
        "context_score": scored["score"],
        "priority_score": priority_score,
        "status": "queued" if priority_score >= minimum else "suppressed",
        "created_at": int(time.time()),
        "metadata": payload.get("metadata") or {},
    }

    if decision["status"] == "queued":
        data["queue"].append(decision)
        sort_queue(data)
    else:
        decision["resolved_at"] = int(time.time())
        data["history"].append(decision)

    write_store(data)

    return {
        "status": decision["status"],
        "decision": decision,
    }


@router.post("/decisions/{decision_id}/resolve")
def resolve_decision(
    decision_id: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    data = read_store()

    decision = next(
        (
            item
            for item in data["queue"]
            if item.get("id") == decision_id
        ),
        None,
    )

    if decision is None:
        raise HTTPException(
            status_code=404,
            detail="Decision not found.",
        )

    data["queue"] = [
        item
        for item in data["queue"]
        if item.get("id") != decision_id
    ]

    decision["status"] = str(
        payload.get("status") or "resolved"
    )
    decision["result"] = payload.get("result") or {}
    decision["resolved_at"] = int(time.time())

    data["history"].append(decision)
    data["history"] = data["history"][-500:]

    write_store(data)

    return {
        "status": "resolved",
        "decision": decision,
    }


@router.delete("/queue")
def clear_queue() -> dict[str, Any]:
    data = read_store()
    now = int(time.time())

    for decision in data["queue"]:
        decision["status"] = "cleared"
        decision["resolved_at"] = now
        data["history"].append(decision)

    count = len(data["queue"])
    data["queue"] = []
    data["history"] = data["history"][-500:]
    write_store(data)

    return {
        "status": "cleared",
        "count": count,
    }


@router.post("/settings")
def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_store()

    for key in (
        "enabled",
        "minimum_score",
        "max_queue",
        "auto_expire_seconds",
    ):
        if key in payload:
            data["settings"][key] = payload[key]

    data["settings"]["minimum_score"] = clamp(
        data["settings"].get("minimum_score", 0.55)
    )
    data["settings"]["max_queue"] = max(
        1,
        min(500, int(data["settings"].get("max_queue", 50))),
    )
    data["settings"]["auto_expire_seconds"] = max(
        60,
        int(data["settings"].get("auto_expire_seconds", 1800)),
    )

    prune(data)
    sort_queue(data)
    write_store(data)

    return {
        "status": "updated",
        "settings": data["settings"],
    }
