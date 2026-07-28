from __future__ import annotations

from typing import Any


def halo_conversation(
    text: str,
    *,
    session_id: str,
    confirm: bool,
) -> dict[str, Any]:
    from services.halo_os.conversation import conversation_engine

    return conversation_engine.process(
        text,
        session_id=session_id,
        confirm=confirm,
    )


def voice_backend_health() -> dict[str, Any]:
    candidates = (
        ("services.voice_ai.orchestrator", "voice_orchestrator"),
        ("services.voice_ai.pipeline", "AudioPipeline"),
    )

    result: dict[str, Any] = {
        "status": "degraded",
        "backend": None,
        "details": {},
    }

    for module_name, attribute_name in candidates:
        try:
            module = __import__(module_name, fromlist=[attribute_name])
            attribute = getattr(module, attribute_name, None)

            if attribute is None:
                continue

            result["status"] = "healthy"
            result["backend"] = module_name
            result["details"][attribute_name] = "available"
            break
        except Exception as exc:
            result["details"][module_name] = (
                f"{type(exc).__name__}: {exc}"
            )

    return result


def tts_speak(text: str) -> dict[str, Any]:
    try:
        from services.voice_ai.orchestrator import voice_orchestrator

        for method_name in ("speak", "say", "synthesize"):
            method = getattr(voice_orchestrator, method_name, None)
            if callable(method):
                result = method(text)

                return {
                    "status": "ok",
                    "backend": f"voice_orchestrator.{method_name}",
                    "result": result,
                }

        return {
            "status": "queued_only",
            "reason": "No compatible TTS method found.",
        }
    except Exception as exc:
        return {
            "status": "queued_only",
            "reason": f"{type(exc).__name__}: {exc}",
        }
