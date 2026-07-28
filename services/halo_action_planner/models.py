from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=120)
    confirm: bool = False


class PlanStep(BaseModel):
    index: int
    kind: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    requires_confirmation: bool = False
