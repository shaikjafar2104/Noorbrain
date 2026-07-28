"""Pydantic request/response models for the learning service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class LearningEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=80)
    source: str = Field(default="manual", min_length=1, max_length=80)
    room: Optional[str] = Field(default=None, max_length=80)
    person_id: Optional[str] = Field(default=None, max_length=120)
    value: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None

    @field_validator("event_type", "source", "room", "person_id")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LearningEventOut(BaseModel):
    id: int
    event_type: str
    source: str
    room: Optional[str]
    person_id: Optional[str]
    value: Optional[float]
    metadata: Dict[str, Any]
    occurred_at: str
    created_at: str
