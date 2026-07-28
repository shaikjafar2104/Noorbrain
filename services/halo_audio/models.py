from __future__ import annotations

from pydantic import BaseModel, Field


class AudioConfig(BaseModel):
    sample_rate: int = Field(default=16000, ge=8000, le=96000)
    channels: int = Field(default=1, ge=1, le=8)
    block_size: int = Field(default=1600, ge=160, le=32768)
    input_device: int | None = None
    output_device: int | None = None
    input_gain: float = Field(default=1.0, ge=0.1, le=10.0)
    output_volume: float = Field(default=1.0, ge=0.0, le=1.0)
    monitor_enabled: bool = False


class AudioActionRequest(BaseModel):
    reason: str = Field(default="manual", min_length=1, max_length=200)
