from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from .context_fusion import context_fusion
from .memory_engine import halo_memory_engine
from .store import halo_brain_store


class HALODecisionEngine:
    def decide(
        self,
        *,
        signal: str,
        person_id: str | None,
        zone: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", signal.strip().casefold())
        context = context_fusion.snapshot(
            person_id=person_id,
            zone=zone,
        )
        memories = halo_memory_engine.recall(
            query=signal,
            person_id=person_id,
            zone=zone,
            limit=10,
        )

        action = {
            "kind": "conversation",
            "name": "respond",
            "arguments": {"text": signal},
            "requires_confirmation": False,
        }
        reason = "Default conversation response."

        if any(term in normalized for term in ("home status", "ghar ka status")):
            action = {
                "kind": "skill",
                "name": "home",
                "arguments": {},
                "requires_confirmation": False,
            }
            reason = "Home-status intent detected."

        elif "camera" in normalized or "vision" in normalized:
            action = {
                "kind": "skill",
                "name": "camera",
                "arguments": {},
                "requires_confirmation": False,
            }
            reason = "Vision intent detected."

        elif "activity" in normalized or "presence" in normalized:
            action = {
                "kind": "skill",
                "name": "activity",
                "arguments": {},
                "requires_confirmation": False,
            }
            reason = "Activity intent detected."

        elif re.search(r"(turn|switch).+(on|off)", normalized):
            action = {
                "kind": "planner",
                "name": "device_action",
                "arguments": {"text": signal},
                "requires_confirmation": True,
            }
            reason = "Potential physical-device action detected."

        elif normalized.startswith(("remember ", "yaad rakho ")):
            value = re.sub(r"^(remember|yaad rakho)\s+", "", signal, flags=re.IGNORECASE)
            action = {
                "kind": "memory",
                "name": "remember",
                "arguments": {
                    "kind": "user_note",
                    "value": value,
                },
                "requires_confirmation": False,
            }
            reason = "Explicit memory request detected."

        decision = halo_brain_store.add("decisions", {
            "decision_id": uuid4().hex,
            "signal": signal,
            "person_id": person_id,
            "zone": zone,
            "reason": reason,
            "action": action,
            "context_summary": {
                "active_people": context.get("presence", {}).get("active_count"),
                "vision_status": context.get("vision", {}).get("status"),
                "today_events": context.get("activity", {}).get("total_events"),
                "family_profiles": context.get("family", {}).get("profile_count"),
            },
            "memory_matches": len(memories),
            "metadata": metadata,
        })

        return {
            "status": "decided",
            "decision": decision,
            "context": context,
            "memories": memories,
        }


halo_decision_engine = HALODecisionEngine()
