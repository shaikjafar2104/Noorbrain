"""Structured AI learning reports."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from .dashboard import LearningDashboardBuilder
from .storage import LearningStore

class LearningReportGenerator:
    def __init__(self, store: LearningStore) -> None: self.store=store

    def generate(self, person_id: Optional[str]=None) -> Dict[str,Any]:
        data=LearningDashboardBuilder(self.store).build(person_id=person_id)
        m=data["monthly"]; w=data["weekly"]
        readiness="collecting_data"
        if m["learning_confidence"]>=70: readiness="strong_baseline"
        elif m["learning_confidence"]>=35: readiness="developing_baseline"
        recommendations=[]
        if m["calendar_coverage_percent"]<50: recommendations.append("Collect events on more days to improve pattern confidence.")
        if m["total_events"]<100: recommendations.append("Continue event logging before enabling high-impact automatic decisions.")
        if not recommendations: recommendations.append("Baseline is healthy; continue monitoring for drift before predictive automation.")
        return {"status":"ok","report_type":"sprint9.1-learning","generated_at":datetime.now(timezone.utc).isoformat(),"person_id":person_id,"readiness":readiness,"headline":f"{m['total_events']} events learned this month with {m['learning_confidence']}% confidence.","metrics":{"monthly_events":m["total_events"],"weekly_events":w["total_events"],"habit_score":m["habit_score"],"learning_confidence":m["learning_confidence"],"trend":m["trend"],"active_days":m["active_days"]},"insights":data["insights"],"recommendations":recommendations}
