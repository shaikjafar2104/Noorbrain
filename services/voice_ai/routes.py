from __future__ import annotations
from fastapi import APIRouter, Query
from .models import ContextRequest, SettingsUpdate, SpeakRequest, TextRequest
from .orchestrator import voice_orchestrator

router = APIRouter(prefix="/api/voice", tags=["Voice AI"])

@router.get("/health")
def health(): return voice_orchestrator.health()

@router.get("/settings")
def get_settings(): return {"status": "ok", "settings": voice_orchestrator.settings_store.load().model_dump()}

@router.patch("/settings")
def update_settings(payload: SettingsUpdate):
    return {"status": "ok", "settings": voice_orchestrator.settings_store.update(payload).model_dump()}

@router.post("/conversation")
def conversation(payload: TextRequest, speak: bool = Query(default=False)):
    return voice_orchestrator.process_text(payload.text, payload.person_id, payload.room, payload.metadata, speak=speak)

@router.get("/history")
def history(limit: int = Query(default=50, ge=1, le=500)):
    return voice_orchestrator.conversation.history(limit)

@router.post("/speak")
def speak(payload: SpeakRequest):
    settings = voice_orchestrator.settings_store.load()
    return voice_orchestrator.tts.speak(payload.text, rate=settings.speech_rate, volume=settings.volume,
                                        voice_name=settings.voice_name, blocking=payload.blocking)

@router.post("/listen")
def listen(seconds: float | None = Query(default=None, ge=1.0, le=30.0), speak: bool = Query(default=True)):
    return voice_orchestrator.listen_once(seconds=seconds, speak=speak)

@router.post("/wake-word/test")
def wake_word_test(payload: TextRequest):
    settings = voice_orchestrator.settings_store.load()
    detected = settings.wake_word.lower() in payload.text.lower()
    return {"status": "ok", "wake_word": settings.wake_word, "detected": detected}

@router.get("/stt/status")
def stt_status(): return {"status": "ok", **voice_orchestrator.stt.status()}

@router.get("/speaker/status")
def speaker_status(): return {"status": "ok", **voice_orchestrator.speaker.status()}

@router.post("/context")
def set_context(payload: ContextRequest):
    return voice_orchestrator.context.set(payload.key, payload.value, payload.person_id, payload.room)

@router.get("/context/{key}")
def get_context(key: str): return voice_orchestrator.context.get(key)

@router.get("/context")
def context_snapshot(limit: int = Query(default=100, ge=1, le=500)):
    return voice_orchestrator.context.snapshot(limit)

@router.get("/memory/recent")
def memory_recent(person_id: str | None = None, limit: int = Query(default=10, ge=1, le=100)):
    return voice_orchestrator.memory.recent_events(person_id, limit)

# NOORBRAIN_SPRINT10_PACK5_HALF1
from .analytics import voice_analytics
from .dashboard import voice_dashboard
from .diagnostics import voice_diagnostics

@router.get("/analytics")
def voice_analytics_endpoint(days: int = Query(default=30, ge=1, le=3650)):
    return voice_analytics.summary(days)

@router.get("/dashboard")
def voice_dashboard_endpoint(days: int = Query(default=30, ge=1, le=3650), recent_limit: int = Query(default=10, ge=1, le=100)):
    return voice_dashboard.snapshot(voice_orchestrator, days=days, recent_limit=recent_limit)

@router.get("/diagnostics")
def voice_diagnostics_endpoint(probe_hardware: bool = Query(default=False)):
    return voice_diagnostics.snapshot(probe_hardware=probe_hardware)

# NOORBRAIN_SPRINT10_PACK5_HALF2
from typing import Any, Dict
from fastapi import Body
from .qa import voice_qa
from .settings_manager import voice_settings_manager

@router.post("/settings")
def replace_voice_settings(payload: Dict[str, Any] = Body(...)):
    return voice_settings_manager.update(voice_orchestrator.settings_store, payload)

@router.post("/test/microphone")
def test_microphone(probe_hardware: bool = Query(default=False)):
    if not probe_hardware:
        return {
            "status": "ok",
            "test": "microphone",
            "package": voice_orchestrator.audio.backend_status(),
            "hardware_probe": "skipped",
        }
    return {"status": "ok", "test": "microphone", **voice_orchestrator.audio.list_input_devices()}

@router.post("/test/speaker")
def test_speaker(speak: bool = Query(default=False)):
    status = voice_orchestrator.speaker.status()
    result = {"status": "ok", "test": "speaker", "speaker": status, "speech": "skipped"}
    if speak:
        settings = voice_orchestrator.settings_store.load()
        result["speech"] = voice_orchestrator.tts.speak(
            "NoorBrain speaker test successful.",
            rate=settings.speech_rate,
            volume=settings.volume,
            voice_name=settings.voice_name,
            blocking=False,
        )
    return result

@router.post("/qa/run")
def run_voice_qa(include_hardware: bool = Query(default=False)):
    return voice_qa.run(voice_orchestrator, include_hardware=include_hardware)

@router.get("/qa/report")
def latest_voice_qa_report():
    return voice_qa.latest()

