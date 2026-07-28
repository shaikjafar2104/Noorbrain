from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .esp32_registry import esp32_registry
from .mqtt_service import mqtt_service
from .rule_engine import rule_engine

router = APIRouter(prefix="/api/automation", tags=["Automation Integration"])


@router.get("/health")
def automation_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "mqtt": mqtt_service.status(),
        "esp32_count": len(esp32_registry.list()),
        "rule_count": len(rule_engine.list()),
    }


@router.get("/mqtt/status")
def mqtt_status() -> dict[str, Any]:
    return mqtt_service.status()


@router.post("/mqtt/start")
def mqtt_start() -> dict[str, Any]:
    return mqtt_service.start()


@router.post("/mqtt/stop")
def mqtt_stop() -> dict[str, Any]:
    return mqtt_service.stop()


@router.post("/mqtt/publish")
def mqtt_publish(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    topic = str(payload.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=422, detail="topic is required")

    return mqtt_service.publish(
        topic,
        payload.get("payload"),
        retain=bool(payload.get("retain", False)),
        qos=int(payload.get("qos", 0)),
    )


@router.get("/esp32")
def esp32_list() -> dict[str, Any]:
    devices = esp32_registry.list()
    return {"status": "ok", "count": len(devices), "devices": devices}


@router.post("/esp32/register")
def esp32_register(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return {"status": "registered", "device": esp32_registry.register(payload)}


@router.post("/esp32/{device_id}/heartbeat")
def esp32_heartbeat(
    device_id: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    try:
        device = esp32_registry.heartbeat(device_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "device": device}


@router.post("/esp32/{device_id}/offline")
def esp32_offline(device_id: str) -> dict[str, Any]:
    try:
        device = esp32_registry.mark_offline(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "device": device}


@router.get("/rules")
def rules_list() -> dict[str, Any]:
    rules = rule_engine.list()
    return {"status": "ok", "count": len(rules), "rules": rules}


@router.post("/rules")
def rules_create(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        rule = rule_engine.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "rule": rule}


@router.patch("/rules/{rule_id}")
def rules_update(
    rule_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        rule = rule_engine.update(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "rule": rule}


@router.delete("/rules/{rule_id}")
def rules_delete(rule_id: str) -> dict[str, Any]:
    if not rule_engine.delete(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return {"status": "deleted", "rule_id": rule_id}


@router.post("/rules/evaluate")
def rules_evaluate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    matches = rule_engine.evaluate(payload)
    return {"status": "ok", "match_count": len(matches), "matches": matches}
