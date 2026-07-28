from __future__ import annotations

import re
from typing import Any


class ContextResolver:
    DEVICE_WORDS = ("light", "fan", "switch", "lamp", "speaker", "camera")
    ROOM_WORDS = ("hall", "kitchen", "bedroom", "office", "garage", "living room")

    def resolve(
        self,
        text: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", text.strip().casefold())
        resolved = text.strip()
        changes: dict[str, Any] = {}

        last_device = context.get("last_device")
        last_room = context.get("last_room")
        last_action = context.get("last_action")

        pronoun_pattern = r"\b(it|that|that one|usko|isko)\b"
        if last_device and re.search(pronoun_pattern, normalized):
            resolved = re.sub(
                pronoun_pattern,
                str(last_device),
                resolved,
                flags=re.IGNORECASE,
            )
            changes["resolved_device_reference"] = last_device

        if any(phrase in normalized for phrase in ("and kitchen too", "kitchen too", "aur kitchen bhi")):
            action = None
            if isinstance(last_action, dict):
                action = last_action.get("action")

            if action in {"on", "off"}:
                resolved = f"Turn Kitchen Light {action}"
                changes["inherited_action"] = action
                changes["resolved_room"] = "Kitchen"

        if any(phrase in normalized for phrase in ("same room", "usi room", "there too")) and last_room:
            resolved = resolved.replace("same room", str(last_room))
            changes["resolved_room"] = last_room

        return {
            "original_text": text,
            "resolved_text": resolved,
            "changes": changes,
        }


context_resolver = ContextResolver()
