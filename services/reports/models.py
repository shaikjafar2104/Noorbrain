"""Shared report models and validation helpers."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class ReportWindow:
    report_type: str
    start_at: datetime
    end_at: datetime
    person_id: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["start_at"] = self.start_at.astimezone(timezone.utc).isoformat()
        data["end_at"] = self.end_at.astimezone(timezone.utc).isoformat()
        return data

@dataclass(frozen=True)
class Score:
    value: float
    confidence: float
    sample_size: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "value": round(max(0.0, min(100.0, self.value)), 2),
            "confidence": round(max(0.0, min(100.0, self.confidence)), 2),
            "sample_size": max(0, int(self.sample_size)),
        }
