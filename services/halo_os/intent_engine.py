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

        # V11.6 Noor system settings control
        setting_commands = (
            (
                ("prayer reminders", "prayer reminder"),
                "islamic",
                "prayer_reminders",
            ),
            (
                ("adhan", "azan"),
                "islamic",
                "adhan_enabled",
            ),
            (
                ("dua reminders", "dua reminder"),
                "islamic",
                "dua_reminders",
            ),
            (
                ("azkar reminders", "azkar reminder", "adhkar reminders"),
                "islamic",
                "azkar_reminders",
            ),
            (
                ("camera",),
                "privacy",
                "camera_enabled",
            ),
            (
                ("microphone", "mic"),
                "privacy",
                "microphone_enabled",
            ),
            (
                ("activity learning",),
                "privacy",
                "activity_learning",
            ),
            (
                ("face recognition",),
                "privacy",
                "face_recognition",
            ),
            (
                ("mobile notifications", "phone notifications"),
                "notifications",
                "mobile_enabled",
            ),
            (
                ("dashboard notifications",),
                "notifications",
                "dashboard_enabled",
            ),
        )

        enable_words = (
            "enable",
            "turn on",
            "switch on",
            "start",
        )

        disable_words = (
            "disable",
            "turn off",
            "switch off",
            "stop",
        )

        for names, section, key in setting_commands:
            if not any(name in normalized for name in names):
                continue

            if any(word in normalized for word in disable_words):
                return IntentResult(
                    "settings_action",
                    0.99,
                    {
                        "section": section,
                        "key": key,
                        "value": False,
                    },
                )

            if any(word in normalized for word in enable_words):
                return IntentResult(
                    "settings_action",
                    0.99,
                    {
                        "section": section,
                        "key": key,
                        "value": True,
                    },
                )

        islamic_words = ("dua", "azkar", "adhkar", "allah name", "99 names")
        play_words = ("play", "chalao", "sunao", "suna do", "lagao")
        if any(word in normalized for word in islamic_words) and any(word in normalized for word in play_words):
            query = re.sub(
                r"\b(?:hey|noor|please|play|chalao|sunao|suna|do|lagao)\b",
                " ",
                normalized,
            )
            return IntentResult(
                "islamic_audio_play",
                0.99,
                {"query": " ".join(query.split())},
            )

        # Islamic Story Mode: "tell me story of prophet yousuf"
        story_match = re.search(
            r"(?:tell me|tell|give me|kahaani sunao|sunao|kahani|history)\s+(?:a\s+)?story(?: about)?\s+(.+)",
            normalized,
        )
        if not story_match:
            story_match = re.search(r"story(?: of)?\s+(.+)", normalized)
        if story_match:
            topic = story_match.group(1).strip(" ?.")
            if topic.startswith("of "):
                topic = topic[3:].strip()
            if topic and len(topic) > 2:
                return IntentResult(
                    "islamic_story",
                    0.95,
                    {"topic": topic},
                )

        return IntentResult(
            "conversation",
            0.40,
            {"text": text.strip()},
        )


intent_engine = IntentEngine()
