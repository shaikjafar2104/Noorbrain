from __future__ import annotations

from typing import Any


class ContextFusion:
    def snapshot(
        self,
        *,
        person_id: str | None = None,
        zone: str | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "person_id": person_id,
            "zone": zone,
            "presence": {},
            "vision": {},
            "activity": {},
            "family": {},
        }

        try:
            from services.person_presence.service import person_presence_service
            context["presence"] = person_presence_service.summary()
        except Exception as exc:
            context["presence"] = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }

        try:
            from services.vision_intelligence.service import vision_intelligence_service
            context["vision"] = vision_intelligence_service.health()
        except Exception as exc:
            context["vision"] = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }

        try:
            from services.activity_intelligence.analytics import activity_analytics
            context["activity"] = activity_analytics.summary(days=1)
        except Exception as exc:
            context["activity"] = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }

        try:
            from services.family_ai.store import family_store
            profiles = family_store.read().get("profiles", [])
            context["family"] = {
                "status": "ok",
                "profile_count": len(profiles),
                "profiles": profiles,
            }
        except Exception as exc:
            context["family"] = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }

        return context


context_fusion = ContextFusion()
