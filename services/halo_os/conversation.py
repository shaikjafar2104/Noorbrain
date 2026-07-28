from __future__ import annotations

from typing import Any

from .context_memory import context_memory
from .intent_engine import intent_engine
from .registry import skill_registry


class ConversationEngine:
    def process(
        self,
        text: str,
        *,
        session_id: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        context_state = context_memory.get(session_id)
        context = context_state.get("context", {})
        intent = intent_engine.classify(text, context)

        if intent.name == "conversation":
            from services.offline_agent.dialogue import local_dialogue

            reply = local_dialogue.chat(text)
            context_memory.update(
                session_id,
                {
                    "last_intent": "conversation",
                    "last_user_text": text,
                },
            )
            return {
                "status": "ok",
                "reply": reply,
                "intent": intent.name,
                "confidence": intent.confidence,
                "context": context_memory.get(session_id)["context"],
            }

        if intent.name == "device_action":
            from services.offline_agent.tool_registry import tool_registry
            from services.offline_agent import tools as _tools  # noqa: F401

            if not confirm:
                return {
                    "status": "needs_confirmation",
                    "reply": (
                        f"Please confirm: turn {intent.arguments['name']} "
                        f"{intent.arguments['state']}?"
                    ),
                    "intent": intent.name,
                    "arguments": intent.arguments,
                }

            result = tool_registry.execute(
                "set_device_state",
                intent.arguments,
            )
            context_memory.update(
                session_id,
                {
                    "last_intent": intent.name,
                    "last_room": self._room_from_name(intent.arguments["name"]),
                    "last_device": intent.arguments["name"],
                    "last_action": {
                        "action": intent.arguments["state"],
                        "device": intent.arguments["name"],
                    },
                },
            )
            return {
                "status": "ok",
                "reply": self._format_device_action(result),
                "intent": intent.name,
                "result": result,
                "context": context_memory.get(session_id)["context"],
            }

        if intent.name == "device_status":
            from services.offline_agent.tool_registry import tool_registry
            from services.offline_agent import tools as _tools  # noqa: F401

            result = tool_registry.execute(
                "get_device_status",
                intent.arguments,
            )
            context_memory.update(
                session_id,
                {
                    "last_intent": intent.name,
                    "last_device": intent.arguments["name"],
                    "last_room": self._room_from_name(intent.arguments["name"]),
                },
            )
            return {
                "status": "ok",
                "reply": self._format_device_status(result),
                "intent": intent.name,
                "result": result,
                "context": context_memory.get(session_id)["context"],
            }

        result = skill_registry.execute(intent.name, intent.arguments)
        context_memory.update(
            session_id,
            {
                "last_intent": intent.name,
                "last_user_text": text,
            },
        )

        return {
            "status": "ok",
            "reply": self._format_skill(intent.name, result),
            "intent": intent.name,
            "confidence": intent.confidence,
            "result": result,
            "context": context_memory.get(session_id)["context"],
        }

    @staticmethod
    def _room_from_name(name: str) -> str | None:
        value = name.casefold()
        for room in ("hall", "kitchen", "bedroom", "office", "garage"):
            if room in value:
                return room.title()
        return None

    @staticmethod
    def _format_device_action(result: dict[str, Any]) -> str:
        if result.get("status") == "not_found":
            return f"I could not find {result.get('query')}."
        device = result.get("device", {})
        return (
            f"{device.get('name', 'Device')} is now "
            f"{str(device.get('state', 'unknown')).upper()}."
        )

    @staticmethod
    def _format_device_status(result: dict[str, Any]) -> str:
        if result.get("status") == "not_found":
            return f"I could not find {result.get('query')}."
        device = result.get("device", {})
        online = "online" if device.get("online") else "offline"
        return (
            f"{device.get('name', 'Device')} is "
            f"{str(device.get('state', 'unknown')).upper()} and {online}."
        )

    @staticmethod
    def _format_skill(name: str, result: dict[str, Any]) -> str:
        if name == "home":
            return "Home status is ready. All available NoorBrain services were checked."
        if name == "devices":
            count = result.get("count", 0)
            return f"{count} registered device{'s' if count != 1 else ''} found."
        if name == "camera":
            return f"Camera status: {result.get('status', 'unknown')}."
        if name == "vision":
            return f"Vision status: {result.get('status', 'unknown')}."
        if name == "activity":
            count = result.get("recorded_events", result.get("count", 0))
            return f"Activity summary contains {count} recorded events."
        if name == "automation":
            counts = result.get("counts", {})
            return (
                f"Automation has {counts.get('rules', 0)} rules, "
                f"{counts.get('scenes', 0)} scenes, and "
                f"{counts.get('routines', 0)} routines."
            )
        if name == "reports":
            return f"Reports status: {result.get('status', 'unknown')}."
        if name == "system":
            return f"NoorBrain system status: {result.get('status', 'unknown')}."
        return "The request completed successfully."


conversation_engine = ConversationEngine()
