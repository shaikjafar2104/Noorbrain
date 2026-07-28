from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    enabled: bool = True
    wake_word: str = "hey noor"
    language: str = "en-US"
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    listen_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
    stt_engine: str = "auto"
    tts_engine: str = "auto"
    voice_name: Optional[str] = None
    speech_rate: int = Field(default=165, ge=80, le=300)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    require_wake_word: bool = False
    save_transcripts: bool = True
    vad_enabled: bool = True
    noise_filter_enabled: bool = True


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    person_id: Optional[str] = None
    room: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    blocking: bool = False


class ContextRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: Any
    person_id: Optional[str] = None
    room: Optional[str] = None


class SettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    wake_word: Optional[str] = Field(default=None, min_length=1, max_length=80)
    language: Optional[str] = None
    sample_rate: Optional[int] = Field(default=None, ge=8000, le=48000)
    listen_seconds: Optional[float] = Field(default=None, ge=1.0, le=30.0)
    stt_engine: Optional[str] = None
    tts_engine: Optional[str] = None
    voice_name: Optional[str] = None
    speech_rate: Optional[int] = Field(default=None, ge=80, le=300)
    volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    require_wake_word: Optional[bool] = None
    save_transcripts: Optional[bool] = None
    vad_enabled: Optional[bool] = None
    noise_filter_enabled: Optional[bool] = None
