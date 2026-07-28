from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RuntimeState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    ERROR = "error"


class ComponentState(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class RuntimeConfig(BaseModel):
    heartbeat_interval_seconds: float = Field(default=5.0, ge=1.0, le=300.0)
    component_timeout_seconds: float = Field(default=8.0, ge=1.0, le=60.0)
    auto_start_voice_runtime: bool = False
    auto_start_tts_worker: bool = False
    enable_recovery: bool = True
    max_recovery_attempts: int = Field(default=3, ge=0, le=20)


class RuntimeActionRequest(BaseModel):
    reason: str = Field(default="manual", min_length=1, max_length=200)


class ComponentSnapshot(BaseModel):
    name: str
    state: ComponentState
    checked_at: str
    latency_ms: float
    detail: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
