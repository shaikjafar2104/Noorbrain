from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntentResult:
    name: str
    confidence: float
    arguments: dict[str, Any]


class IntentEngine:
    def classify(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        context = context or {}
        normalized = re.sub(r"\s+", " ", text.strip().casefold())

        if any(x in normalized for x in ("ghar ka status", "home status", "house status")):
            return IntentResult("home", 0.99, {})

        if any(x in normalized for x in ("camera status", "camera online", "camera health")):
            return IntentResult("camera", 0.99, {})

        if any(x in normalized for x in ("vision status", "person detection status")):
            return IntentResult("vision", 0.99, {})

        if any(x in normalized for x in ("activity summary", "activity status", "recent activity")):
            return IntentResult("activity", 0.98, {})

        if any(x in normalized for x in ("automation summary", "automation status")):
            return IntentResult("automation", 0.98, {})

        if any(x in normalized for x in ("report summary", "reports summary", "ai insights")):
            return IntentResult("reports", 0.97, {})

        if any(x in normalized for x in ("system health", "noorbrain health", "health check")):
            return IntentResult("system", 0.98, {})

        if any(x in normalized for x in ("what devices", "list devices", "registered devices")):
            return IntentResult("devices", 0.99, {})

        if normalized in {"and the kitchen too", "kitchen too", "aur kitchen bhi"}:
            last_action = context.get("last_action")
            if isinstance(last_action, dict) and last_action.get("action") in {"on", "off"}:
                return IntentResult(
                    "device_action",
                    0.92,
                    {
                        "name": "Kitchen Light",
                        "state": last_action["action"],
                    },
                )

        match = re.search(
            r"(?:turn|switch)\s+(?:the\s+)?(.+?)\s+(on|off)$",
            normalized,
        )
        if match:
            return IntentResult(
                "device_action",
                0.99,
                {
                    "name": match.group(1).strip(),
                    "state": match.group(2),
                },
            )

        match = re.search(
            r"(?:status of|what is the status of)\s+(?:the\s+)?(.+?)(?:\?|$)",
            normalized,
        )
        if match:
            return IntentResult(
                "device_status",
                0.95,
                {"name": match.group(1).strip()},
            )

        return IntentResult(
            "conversation",
            0.40,
            {"text": text.strip()},
        )


intent_engine = IntentEngine()
