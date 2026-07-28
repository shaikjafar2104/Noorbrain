from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VoiceCommandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="voice-default", min_length=1, max_length=120)
    confirm: bool = False
    speak: bool = False


class VoiceQueueItem(BaseModel):
    id: str
    text: str
    priority: int = 0
    status: Literal["queued", "speaking", "done", "cancelled"] = "queued"
    metadata: dict[str, Any] = Field(default_factory=dict)
