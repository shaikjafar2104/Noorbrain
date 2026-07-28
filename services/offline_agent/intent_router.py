from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Intent:
    name: str
    arguments: dict[str, Any]
    confidence: float


class IntentRouter:
    DEVICE_STATUS_PATTERNS = (
        r"(?:status of|what is the status of|is)\s+(?:the\s+)?(.+?)(?:\s+on|\s+off|\?|$)",
        r"(.+?)\s+(?:status|state)$",
    )

    def route(self, text: str) -> Intent:
        original = text.strip()
        normalized = re.sub(r"\s+", " ", original.casefold()).strip(" ?!.")

        if any(phrase in normalized for phrase in (
            "home status", "house status", "ghar ka status", "ghar status",
            "overall status", "everything status", "status of my home",
        )):
            return Intent("home_status", {}, 0.99)

        if any(phrase in normalized for phrase in (
            "system health", "system status", "noorbrain health",
            "noorbrain status", "health check",
        )):
            return Intent("system_health", {}, 0.99)

        if any(phrase in normalized for phrase in (
            "what skills", "list skills", "show skills", "halo skills",
            "what can you do", "tum kya kar sakte",
        )):
            return Intent("skills_status", {}, 0.98)

        if any(phrase in normalized for phrase in (
            "camera status", "camera online", "camera connected",
            "is camera working", "camera ka status",
        )):
            return Intent("camera_status", {}, 0.99)

        if any(phrase in normalized for phrase in (
            "vision status", "vision engine status", "is vision running",
            "detection status", "vision ka status",
        )):
            return Intent("vision_status", {}, 0.99)

        if any(phrase in normalized for phrase in (
            "activity summary", "activity status", "recent activity",
            "who is home", "anyone home", "koi ghar mein hai",
            "ghar mein koi hai", "hall mein koi hai",
        )):
            return Intent("activity_summary", {}, 0.98)

        if any(phrase in normalized for phrase in (
            "report summary", "reports summary", "learning summary",
            "insights summary", "ai insights summary",
        )):
            return Intent("reports_summary", {}, 0.98)

        if any(phrase in normalized for phrase in (
            "what devices", "list devices", "registered devices", "show devices",
        )):
            return Intent("list_devices", {}, 0.98)

        if any(phrase in normalized for phrase in (
            "automation summary", "automation status", "automation diagnostics",
        )):
            return Intent("automation_summary", {}, 0.98)

        if any(phrase in normalized for phrase in (
            "list scenes", "show scenes", "what scenes",
        )):
            return Intent("list_scenes", {}, 0.97)

        if any(phrase in normalized for phrase in (
            "list routines", "show routines", "what routines",
        )):
            return Intent("list_routines", {}, 0.97)

        match = re.search(
            r"(?:turn|switch)\s+(?:the\s+)?(.+?)\s+(on|off)$",
            normalized,
        )
        if match:
            return Intent(
                "set_device_state",
                {"name": match.group(1).strip(), "state": match.group(2)},
                0.99,
            )

        match = re.search(
            r"(?:run|activate|start)\s+(?:the\s+)?(.+?)\s+scene$",
            normalized,
        )
        if match:
            return Intent(
                "run_scene",
                {"name": match.group(1).strip()},
                0.98,
            )

        for pattern in self.DEVICE_STATUS_PATTERNS:
            match = re.search(pattern, normalized)
            if match:
                name = match.group(1).strip(" ?.")
                if name:
                    return Intent("get_device_status", {"name": name}, 0.90)

        return Intent("conversation", {"text": original}, 0.40)


intent_router = IntentRouter()
