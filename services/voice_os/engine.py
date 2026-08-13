from __future__ import annotations

from typing import Any

from .adapters import halo_conversation, tts_speak
from .queue import voice_queue
from .session import voice_sessions


class VoiceOSEngine:
    STOP_PHRASES = {
        "halo stop",
        "stop speaking",
        "stop",
        "cancel voice",
        "be quiet",
    }

    def process(
        self,
        text: str,
        *,
        session_id: str,
        confirm: bool = False,
        speak: bool = False,
    ) -> dict[str, Any]:
        normalized = " ".join(text.casefold().split()).strip(" ?!.")

        if normalized in self.STOP_PHRASES:
            cancelled = voice_queue.cancel_all()
            session = voice_sessions.touch(
                session_id,
                state="stopped",
                text=text,
                reply="Stopped.",
            )

            return {
                "status": "ok",
                "reply": "Stopped.",
                "action": "stop",
                "cancelled_items": cancelled,
                "session": session,
            }

        voice_sessions.touch(
            session_id,
            state="thinking",
            text=text,
        )

        # Fast local commands: bypass Ollama.
        time_phrases = {
            "what time is it",
            "what is the time",
            "tell me the time",
            "current time",
            "time",
        }

        if normalized in time_phrases:
            from datetime import datetime

            now = datetime.now()
            reply = now.strftime("It is %I:%M %p.").replace(" 0", " ")

            result = {
                "status": "ok",
                "reply": reply,
                "intent": "local_time",
                "action": "get_time",
            }
        else:
            result = halo_conversation(
                text,
                session_id=session_id,
                confirm=confirm,
            )

        reply = str(result.get("reply") or "").strip()
        queue_item = None
        speech_result = None

        if reply and result.get("status") == "ok":
            queue_item = voice_queue.add(
                reply,
                priority=10,
                metadata={
                    "session_id": session_id,
                    "intent": result.get("intent"),
                },
            )

            if speak:
                speech_result = tts_speak(reply)

        state = (
            "confirmation"
            if result.get("status") == "needs_confirmation"
            else "ready"
        )

        session = voice_sessions.touch(
            session_id,
            state=state,
            reply=reply,
        )

        return {
            **result,
            "voice": {
                "queue_item": queue_item,
                "speech": speech_result,
                "speak_requested": speak,
            },
            "session": session,
        }


voice_os_engine = VoiceOSEngine()
