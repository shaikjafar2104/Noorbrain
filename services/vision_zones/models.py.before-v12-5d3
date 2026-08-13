from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ZonePoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    camera_id: str = Field(default="primary", min_length=1, max_length=120)
    points: list[ZonePoint] = Field(min_length=3)
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class MotionSample(BaseModel):
    camera_id: str = Field(default="primary", min_length=1, max_length=120)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="vision_engine", min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
