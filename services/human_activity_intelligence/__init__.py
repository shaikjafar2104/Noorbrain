"""Human Activity Intelligence v1.0.0

Consumes existing person-track/zone/object data from the vision pipeline
and emits richer temporal activity observations into the existing rule path
(services.reminder_rules / services.islamic_intelligence_v12).

Does NOT replace the activity_engine zone-presence tracker.
"""
from .engine import human_activity_intelligence
from .store import activity_store
from .routes import router

__all__ = ["human_activity_intelligence", "activity_store", "router"]
