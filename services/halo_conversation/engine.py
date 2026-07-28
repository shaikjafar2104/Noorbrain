from __future__ import annotations

from typing import Any

from .clarification_engine import clarification_engine
from .context_resolver import context_resolver
from .session_manager import conversation_sessions


class HALOConversationEngine:
    def process(
        self,
        text: str,
        *,
        session_id: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        session = conversation_sessions.get(session_id)
        context = dict(session.get("context") or {})

        conversation_sessions.append_turn(
            session_id,
            role="user",
            text=text,
        )

        resolved = context_resolver.resolve(text, context)
        clarification = clarification_engine.evaluate(
            text,
            resolved["resolved_text"],
            context,
        )

        if clarification["required"]:
            conversation_sessions.set_clarification(
                session_id,
                clarification,
            )
            conversation_sessions.append_turn(
                session_id,
                role="assistant",
                text=clarification["question"],
                intent="clarification",
                metadata=clarification,
            )

            return {
                "status": "needs_clarification",
                "reply": clarification["question"],
                "clarification": clarification,
                "resolution": resolved,
                "session_id": session_id,
            }

        conversation_sessions.set_clarification(session_id, None)

        from services.halo_os.conversation import conversation_engine

        result = conversation_engine.process(
            resolved["resolved_text"],
            session_id=session_id,
            confirm=confirm,
        )

        reply = str(result.get("reply") or "")
        intent = result.get("intent")

        metadata: dict[str, Any] = {
            "resolution": resolved,
            "halo_result_status": result.get("status"),
        }

        conversation_sessions.append_turn(
            session_id,
            role="assistant",
            text=reply,
            intent=intent,
            metadata=metadata,
        )

        context_update: dict[str, Any] = {
            "last_intent": intent,
            "last_user_text": text,
            "last_resolved_text": resolved["resolved_text"],
        }

        result_context = result.get("context")
        if isinstance(result_context, dict):
            for key in (
                "last_room",
                "last_device",
                "last_action",
                "pending_action",
            ):
                if key in result_context:
                    context_update[key] = result_context[key]

        conversation_sessions.update_context(
            session_id,
            context_update,
        )

        return {
            **result,
            "session_id": session_id,
            "resolution": resolved,
            "conversation_context": conversation_sessions.get(session_id).get("context", {}),
        }


halo_conversation_engine = HALOConversationEngine()
