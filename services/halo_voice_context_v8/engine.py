from __future__ import annotations

from typing import Any

from services.halo_conversation_memory_v8.store import (
    conversation_memory_store,
)


class VoiceContextEngine:
    def build(
        self,
        session_id: str,
        utterance: str,
        limit: int = 12,
    ) -> dict[str, Any]:
        session = conversation_memory_store.context(session_id, limit)
        messages = session.get("messages", [])
        facts = session.get("facts", {})

        recent = [
            {
                "role": item.get("role", "user"),
                "text": item.get("text", ""),
            }
            for item in messages
            if str(item.get("text") or "").strip()
        ]

        fact_lines = [
            f"{key}: {value}"
            for key, value in sorted(facts.items())
        ]

        system_prompt = (
            "You are HALO, NoorBrain's concise home assistant. "
            "Use remembered context only when relevant. "
            "Never invent a family preference or device state."
        )
        if fact_lines:
            system_prompt += "\nRemembered facts:\n- " + "\n- ".join(fact_lines)

        return {
            "session_id": session_id,
            "utterance": utterance.strip(),
            "system_prompt": system_prompt,
            "recent_messages": recent,
            "facts": facts,
            "message_count": len(recent),
        }

    def remember_exchange(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
        source: str = "voice",
    ) -> dict[str, Any]:
        user_message = conversation_memory_store.remember(
            session_id,
            "user",
            user_text,
            {"source": source},
        )
        assistant_message = conversation_memory_store.remember(
            session_id,
            "assistant",
            assistant_text,
            {"source": source},
        )
        return {
            "user_message": user_message,
            "assistant_message": assistant_message,
        }


voice_context_engine = VoiceContextEngine()
