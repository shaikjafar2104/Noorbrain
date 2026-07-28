from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=120)
    confirm: bool = False

class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    status: Literal["ok", "needs_confirmation", "error"]
    reply: str
    tool: ToolCall | None = None
    result: dict[str, Any] | None = None
