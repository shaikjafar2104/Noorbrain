from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class DeviceType(StrEnum):
    LIGHT = "light"
    FAN = "fan"
    PLUG = "plug"
    RELAY = "relay"
    SWITCH = "switch"
    SENSOR = "sensor"
    MOTION_SENSOR = "motion_sensor"
    DOOR_SENSOR = "door_sensor"
    TEMPERATURE_SENSOR = "temperature_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"
    CAMERA = "camera"
    OTHER = "other"

class DeviceState(StrEnum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"

class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    device_type: DeviceType
    room: str = Field(default="Unassigned", min_length=1, max_length=120)
    state: DeviceState = DeviceState.UNKNOWN
    online: bool = False
    ip_address: str | None = Field(default=None, max_length=64)
    mac_address: str | None = Field(default=None, max_length=64)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "room")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value

class Device(DeviceCreate):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "Device":
        return self.model_copy(update={"updated_at": utc_now_iso()})
