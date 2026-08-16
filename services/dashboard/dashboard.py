"""
============================================================
Project : NoorBrain
Module  : Dashboard Service
Sprint  : 4.5
Purpose :
    Collect information from NoorBrain services and expose
    a single dashboard snapshot.

This module DOES NOT modify any service.
It only reads existing APIs.
============================================================
"""

from services.habit_engine import habit_engine
from services.habit_ai import habit_ai
from services.habit_ai.predictor import habit_predictor
from services.habit_ai.recommendation import habit_recommendation
from services.human_activity_intelligence.engine import human_activity_intelligence
from services.human_activity_intelligence.store import activity_store


class DashboardService:

    def snapshot(self):

        habits = habit_engine.summary(300)

        insights = habit_ai.analyse(habits)

        predictions = habit_predictor.predict(habits)

        recommendation = (
            habit_recommendation.evaluate(habits)
        )

        summary = {
            "mode":
                recommendation.get("mode"),
            "recommendation":
                recommendation.get("recommendation"),
            "confidence":
                recommendation.get(
                    "confidence_percent"
                ),
            "expected_time":
                recommendation.get(
                    "expected_time"
                ),
            "current_hour":
                recommendation.get(
                    "current_hour"
                ),
            "context":
                recommendation.get(
                    "context",
                    {}
                )
        }

        return {

            "status": "running",

            "version": "Sprint 4.5",

            "habit": habits,

            "insights": insights,

            "predictions": predictions,

            "recommendation": recommendation,

            "summary": summary,

            "human_activity": {
                "active_sessions": human_activity_intelligence.active_sessions(),
                "recent_events": activity_store.recent_events(limit=20),
                "session_count": activity_store.session_count(),
                "event_count": activity_store.event_count(),
                "long_sitting_count": activity_store.count_events("long_sitting"),
                "inactivity_count": activity_store.count_events("inactivity"),
                "possible_phone_use_count": activity_store.count_events("possible_phone_use"),
                "possible_tv_context_count": activity_store.count_events("possible_tv_context"),
                "recent_patterns": activity_store.list_patterns(limit=10),
                "pending_suggestions": activity_store.list_suggestions(status="new", limit=10),
                "snapshot_enabled": activity_store.get_setting("snapshot_enabled") in {"1", "true", "yes"},
            },
        }


dashboard = DashboardService()
