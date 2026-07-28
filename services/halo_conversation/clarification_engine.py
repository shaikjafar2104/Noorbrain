from __future__ import annotations

import re
from typing import Any


class ClarificationEngine:
    def evaluate(
        self,
        text: str,
        resolved_text: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", resolved_text.strip().casefold())

        if normalized in {"turn it on", "turn it off", "switch it on", "switch it off"}:
            return {
                "required": True,
                "question": "Which device should I control?",
                "reason": "missing_device",
                "options": [],
            }

        if normalized.startswith("turn ") and normalized.endswith((" on", " off")):
            body = normalized[5:]
            device = body.rsplit(" ", 1)[0].strip()
            if device.startswith("the "):
                device = device[4:].strip()

            if device in {"light", "fan", "device", "switch"}:
                room = context.get("last_room")

                if not room:
                    return {
                        "required": True,
                        "question": f"Which room's {device} do you mean?",
                        "reason": "missing_room",
                        "options": ["Hall", "Kitchen", "Bedroom", "Office"],
                    }

        if normalized in {"yes", "no", "haan", "nahi"} and not context.get("pending_action"):
            return {
                "required": True,
                "question": "What would you like me to confirm?",
                "reason": "orphan_confirmation",
                "options": [],
            }

        return {
            "required": False,
            "question": None,
            "reason": None,
            "options": [],
        }


clarification_engine = ClarificationEngine()
