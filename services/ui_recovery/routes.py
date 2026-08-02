from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(
    prefix="/api/ui-recovery",
    tags=["UI Recovery"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ui_recovery",
        "version": "1.0.0",
    }


@router.get("/mobile/status")
async def mobile_status() -> dict[str, Any]:
    from services.mobile_notifications.store import (
        mobile_notification_store,
    )
    from services.mobile_notifications.dnd import (
        notification_dnd_service,
    )

    summary = await asyncio.to_thread(
        mobile_notification_store.summary
    )
    dnd = await asyncio.to_thread(
        notification_dnd_service.status
    )

    snoozed = [
        item
        for item in await asyncio.to_thread(
            mobile_notification_store.list,
            limit=5000,
            include_archived=True,
        )
        if item.get("status") == "snoozed"
    ]

    return {
        "status": "ok",
        "summary": summary,
        "dnd": dnd,
        "snoozed_count": len(snoozed),
    }


@router.post("/mobile/toggle-dnd")
async def toggle_dnd() -> dict[str, Any]:
    from services.mobile_notifications.store import (
        mobile_notification_store,
    )

    data = await asyncio.to_thread(
        mobile_notification_store.read
    )
    enabled = not bool(
        data["settings"].get("dnd_enabled", False)
    )

    settings = await asyncio.to_thread(
        mobile_notification_store.update_settings,
        {"dnd_enabled": enabled},
    )

    return {
        "status": "updated",
        "dnd_enabled": enabled,
        "settings": settings,
    }


@router.post("/mobile/reactivate-snoozed")
async def reactivate_snoozed() -> dict[str, Any]:
    from services.mobile_notifications.acknowledgements import (
        notification_acknowledgement_service,
    )

    return await asyncio.to_thread(
        notification_acknowledgement_service.due_snoozed
    )


@router.post("/mobile/mark-all-read")
async def mark_all_read() -> dict[str, Any]:
    from services.mobile_notifications.store import (
        mobile_notification_store,
    )

    updated = await asyncio.to_thread(
        mobile_notification_store.mark_all_read
    )

    return {
        "status": "updated",
        "updated_count": updated,
    }


@router.get("/automation/overview")
async def automation_overview() -> dict[str, Any]:
    from services.smart_automation.store import automation_store

    rules = await asyncio.to_thread(
        automation_store.list_rules
    )
    runs = await asyncio.to_thread(
        automation_store.list_runs,
        100,
    )

    return {
        "status": "ok",
        "rule_count": len(rules),
        "enabled_count": sum(
            1
            for rule in rules
            if rule.get("enabled", True)
        ),
        "rules": rules,
        "runs": runs,
    }


@router.post("/automation/rules")
async def create_automation_rule(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    from services.smart_automation.store import automation_store

    name = str(payload.get("name") or "").strip()
    zone = str(payload.get("zone") or "").strip()
    condition = str(
        payload.get("condition") or "person_present"
    )
    action = str(
        payload.get("action") or "halo_speak"
    )
    message = str(
        payload.get("message")
        or "Someone is in the room."
    ).strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Rule name is required.",
        )

    conditions: list[dict[str, Any]] = []

    if zone:
        conditions.append({
            "kind": "zone",
            "operator": "eq",
            "value": zone,
        })

    if condition == "person_present":
        conditions.append({
            "kind": "presence_count",
            "operator": "gte",
            "value": 1,
        })
    elif condition == "person_entered":
        conditions.append({
            "kind": "event_type",
            "operator": "eq",
            "value": "person_entered",
        })
    elif condition == "person_exited":
        conditions.append({
            "kind": "event_type",
            "operator": "eq",
            "value": "person_exited",
        })

    if action == "halo_speak":
        actions = [{
            "kind": "halo",
            "name": "speak",
            "arguments": {
                "text": message,
            },
        }]
    elif action == "remember":
        actions = [{
            "kind": "memory",
            "name": "remember",
            "arguments": {
                "kind": "automation_note",
                "value": message,
            },
        }]
    else:
        actions = [{
            "kind": "halo",
            "name": "respond",
            "arguments": {
                "text": message,
            },
        }]

    rule = await asyncio.to_thread(
        automation_store.create_rule,
        {
            "name": name,
            "description":
                payload.get("description"),
            "condition_mode": "all",
            "conditions": conditions,
            "schedule": {
                "kind": "manual",
            },
            "actions": actions,
            "metadata": {
                "created_by":
                    "ui_recovery",
                "ui_mode":
                    "friendly",
            },
        },
    )

    return {
        "status": "created",
        "rule": rule,
    }


@router.post("/automation/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
) -> dict[str, Any]:
    from services.smart_automation.store import automation_store

    rule = await asyncio.to_thread(
        automation_store.get_rule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail="Rule not found.",
        )

    updated = await asyncio.to_thread(
        automation_store.update_rule,
        rule_id,
        {
            "enabled":
                not bool(
                    rule.get("enabled", True)
                )
        },
    )

    return {
        "status": "updated",
        "rule": updated,
    }


@router.post("/automation/rules/{rule_id}/run")
async def run_rule(
    rule_id: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    from services.smart_automation.store import automation_store
    from services.smart_automation.action_executor import (
        automation_action_executor,
    )

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
        "event_type": "manual_ui_run",
        "zone": payload.get("zone"),
        "person_id": payload.get("person_id"),
        "metadata": {
            "source": "ui_recovery",
        },
    }

    return await asyncio.to_thread(
        automation_action_executor.execute_actions,
        rule=rule,
        context=context,
        confirmed=True,
    )


@router.delete("/automation/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
) -> dict[str, Any]:
    from services.smart_automation.store import automation_store

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
