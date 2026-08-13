from __future__ import annotations

from typing import Any

from .service import noor_settings


def apply_runtime_settings() -> dict[str, Any]:
    settings = noor_settings.get_all()

    result: dict[str, Any] = {
        "status": "ok",
        "applied": [],
        "errors": [],
    }

    # Wake words
    try:
        from services.voice_os.wakeword import wakeword_engine

        assistant = settings.get("assistant", {})
        wake_words = list(
            assistant.get("wake_words")
            or ["noor", "hey noor", "hello noor"]
        )

        wakeword_engine.configure(wake_words)

        result["applied"].append("assistant.wake_words")

    except Exception as exc:
        result["errors"].append(
            f"wake_words: {type(exc).__name__}: {exc}"
        )

    return result


def runtime_snapshot() -> dict[str, Any]:
    settings = noor_settings.get_all()

    assistant = settings.get("assistant", {})
    voice = settings.get("voice", {})
    ai = settings.get("ai", {})
    islamic = settings.get("islamic", {})
    privacy = settings.get("privacy", {})
    notifications = settings.get("notifications", {})

    wake_status = None

    try:
        from services.voice_os.wakeword import wakeword_engine
        wake_status = wakeword_engine.status()
    except Exception:
        pass

    return {
        "assistant": assistant,
        "voice": voice,
        "ai": ai,
        "islamic": islamic,
        "privacy": privacy,
        "notifications": notifications,
        "wakeword_runtime": wake_status,
    }
