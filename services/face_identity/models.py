from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    family_profile_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingEnroll(BaseModel):
    person_id: str = Field(min_length=1, max_length=120)
    embedding: list[float] = Field(min_length=16, max_length=4096)
    source: str = Field(default="manual", min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageEnroll(BaseModel):
    person_id: str = Field(min_length=1, max_length=120)
    image_base64: str = Field(min_length=4)
    source: str = Field(default="camera", min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecognitionRequest(BaseModel):
    embedding: list[float] = Field(min_length=16, max_length=4096)
    threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    zone: str | None = Field(default=None, max_length=120)
    track_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageRecognitionRequest(BaseModel):
    image_base64: str = Field(min_length=4)
    threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    zone: str | None = Field(default=None, max_length=120)
    track_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
