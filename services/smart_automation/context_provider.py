from __future__ import annotations
from typing import Any

class AutomationContextProvider:
    def snapshot(
        self,
        *,
        event_type: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "event_type": event_type,
            "person_id": person_id,
            "zone": zone,
            "metadata": metadata or {},
            "presence": {},
            "vision": {},
            "brain": {},
        }

        try:
            from services.person_presence.service import person_presence_service
            context["presence"] = person_presence_service.summary()
        except Exception:
            context["presence"] = {"status": "unavailable"}

        try:
            from services.vision_intelligence.service import vision_intelligence_service
            context["vision"] = vision_intelligence_service.health()
        except Exception:
            context["vision"] = {"status": "unavailable"}

        try:
            from services.halo_brain.brain import halo_brain
            context["brain"] = halo_brain.health()
        except Exception:
            context["brain"] = {"status": "unavailable"}

        return context

automation_context_provider = AutomationContextProvider()
