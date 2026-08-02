"""Dashboard-ready adapter for report summaries and export actions."""
from __future__ import annotations
from typing import Any, Dict


class DashboardAdapter:
    @staticmethod
    def build(report: Dict[str, Any]) -> Dict[str, Any]:
        summary = report.get("summary", {}) or {}
        insights = report.get("insights", {}) or {}
        cards = [
            {"id": "total-events", "label": "Total events", "value": summary.get("total_events", 0)},
            {"id": "active-days", "label": "Active days", "value": summary.get("active_days", 0)},
            {"id": "habit-score", "label": "Habit score", "value": insights.get("habit_score", 0)},
            {"id": "prayer-consistency", "label": "Prayer consistency", "value": insights.get("prayer_consistency_score", 0)},
            {"id": "learning-confidence", "label": "Learning confidence", "value": insights.get("learning_confidence", 0)},
            {"id": "top-room", "label": "Top room", "value": summary.get("top_room") or "No data"},
        ]
        return {
            "status": "ok",
            "service": "reports-dashboard",
            "report_type": report.get("report_type"),
            "generated_at": report.get("generated_at"),
            "cards": cards,
            "recommendations": insights.get("recommendations", []),
            "trend": insights.get("trend"),
            "export_formats": ["json", "html", "csv", "markdown", "pdf"],
        }
