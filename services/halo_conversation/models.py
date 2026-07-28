from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=120)
    confirm: bool = False


class ConversationTurn(BaseModel):
    role: str
    text: str
    timestamp: str
    intent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
