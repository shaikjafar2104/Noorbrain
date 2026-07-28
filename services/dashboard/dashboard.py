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

            "summary": summary
        }


dashboard = DashboardService()
