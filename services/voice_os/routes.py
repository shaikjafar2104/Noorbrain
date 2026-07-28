from __future__ import annotations

import asyncio
import base64
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .adapters import voice_backend_health
from .engine import voice_os_engine
from .models import VoiceCommandRequest
from .queue import voice_queue
from .session import voice_sessions
from .streaming import audio_stream_buffer
from .stt_adapter import stt_adapter
from .tts_worker import tts_worker
from .wakeword import wakeword_engine

router = APIRouter(prefix="/api/voice-os", tags=["Voice OS"])


@router.get("/health")
async def health() -> dict[str, Any]:
    backend = await asyncio.to_thread(voice_backend_health)

    return {
        "status": "healthy",
        "service": "voice_os",
        "version": "3.0-phaseB-pack2",
        "halo_os": "connected",
        "voice_backend": backend,
        "wakeword": wakeword_engine.status(),
        "stream": audio_stream_buffer.status(),
        "stt": stt_adapter.health(),
        "tts_worker": tts_worker.status(),
        "queue_size": len(voice_queue.list()),
        "session_count": len(voice_sessions.list()),
    }


@router.post("/command")
async def command(payload: VoiceCommandRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            voice_os_engine.process,
            payload.text,
            session_id=payload.session_id,
            confirm=payload.confirm,
            speak=payload.speak,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post("/wakeword/detect")
async def wakeword_detect(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    text = str(payload.get("text") or "")
    event = wakeword_engine.detect_text(text)

    return {
        "status": "ok",
        "detected": event.detected,
        "phrase": event.phrase,
        "confidence": event.confidence,
        "armed": wakeword_engine.is_armed(),
    }


@router.get("/wakeword/status")
async def wakeword_status() -> dict[str, Any]:
    return wakeword_engine.status()


@router.post("/wakeword/configure")
async def wakeword_configure(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return wakeword_engine.configure(
            list(payload.get("wake_words") or [])
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/stream/chunk")
async def stream_chunk(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    encoded = str(payload.get("audio_base64") or "")

    try:
        return audio_stream_buffer.append_base64(encoded)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/stream/status")
async def stream_status() -> dict[str, Any]:
    return audio_stream_buffer.status()


@router.post("/stream/clear")
async def stream_clear() -> dict[str, Any]:
    count = audio_stream_buffer.clear()
    return {"status": "cleared", "removed_chunks": count}


@router.post("/stream/transcribe")
async def stream_transcribe(
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    audio = audio_stream_buffer.pop_all()
    sample_rate = int(payload.get("sample_rate", 16000))
    channels = int(payload.get("channels", 1))

    return await asyncio.to_thread(
        stt_adapter.transcribe_pcm16,
        audio,
        sample_rate=sample_rate,
        channels=channels,
    )


@router.post("/tts/start")
async def tts_start() -> dict[str, Any]:
    return await asyncio.to_thread(tts_worker.start)


@router.post("/tts/stop")
async def tts_stop() -> dict[str, Any]:
    return await asyncio.to_thread(tts_worker.stop)


@router.get("/tts/status")
async def tts_status() -> dict[str, Any]:
    return tts_worker.status()


@router.get("/sessions")
async def sessions() -> dict[str, Any]:
    items = await asyncio.to_thread(voice_sessions.list)
    return {"status": "ok", "count": len(items), "sessions": items}


@router.get("/sessions/{session_id}")
async def session(session_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "session": await asyncio.to_thread(
            voice_sessions.get,
            session_id,
        ),
    }


@router.get("/queue")
async def queue_list() -> dict[str, Any]:
    items = await asyncio.to_thread(voice_queue.list)
    return {"status": "ok", "count": len(items), "items": items}


@router.post("/queue/next")
async def queue_next() -> dict[str, Any]:
    item = await asyncio.to_thread(voice_queue.next)
    return {"status": "ok", "item": item}


@router.post("/queue/{item_id}/complete")
async def queue_complete(item_id: str) -> dict[str, Any]:
    try:
        item = await asyncio.to_thread(
            voice_queue.complete,
            item_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "completed", "item": item}


@router.post("/stop")
async def stop(
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "voice-default")

    return await asyncio.to_thread(
        voice_os_engine.process,
        "HALO stop",
        session_id=session_id,
        confirm=False,
        speak=False,
    )
