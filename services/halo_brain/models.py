from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BrainRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=120)
    person_id: str | None = Field(default=None, max_length=120)
    zone: str | None = Field(default=None, max_length=120)
    confirm: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryWrite(BaseModel):
    kind: str = Field(min_length=1, max_length=120)
    value: Any
    person_id: str | None = Field(default=None, max_length=120)
    zone: str | None = Field(default=None, max_length=120)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    signal: str = Field(min_length=1, max_length=4000)
    person_id: str | None = Field(default=None, max_length=120)
    zone: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
