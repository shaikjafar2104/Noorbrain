"""Dashboard-ready summaries and heatmap data."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from .patterns import DailyPatternBuilder, WeeklyPatternBuilder, MonthlyPatternBuilder
from .storage import LearningStore

class LearningDashboardBuilder:
    def __init__(self, store: LearningStore) -> None: self.store=store

    def build(self, person_id: Optional[str]=None) -> Dict[str,Any]:
        daily=DailyPatternBuilder(self.store).build(person_id=person_id)
        weekly=WeeklyPatternBuilder(self.store).build(person_id=person_id)
        monthly=MonthlyPatternBuilder(self.store).build(person_id=person_id)
        end=datetime.now(timezone.utc); start=end-timedelta(days=30)
        clauses=["occurred_at >= ?","occurred_at < ?"]; values=[start.isoformat(),end.isoformat()]
        if person_id: clauses.append("person_id = ?"); values.append(person_id)
        rows=self.store.aggregate(f"SELECT CAST(strftime('%w',occurred_at) AS INTEGER) AS sqlite_day, CAST(strftime('%H',occurred_at) AS INTEGER) AS hour, COUNT(*) AS count FROM learning_events WHERE {' AND '.join(clauses)} GROUP BY sqlite_day,hour",values)
        heatmap=[[0 for _ in range(24)] for _ in range(7)]
        for row in rows:
            # SQLite Sunday=0; API Monday=0.
            day=(int(row["sqlite_day"])+6)%7; heatmap[day][int(row["hour"])]=int(row["count"])
        insights=[]
        if monthly["total_events"]==0: insights.append("Not enough events yet; keep NoorBrain running to build a baseline.")
        else:
            insights.append(f"Monthly activity trend is {monthly['trend']}.")
            if monthly["peak_hour"] is not None: insights.append(f"Peak activity is around {monthly['peak_hour']:02d}:00 UTC.")
            if monthly["top_room"]: insights.append(f"Most active room is {monthly['top_room']}.")
            insights.append(f"Learning confidence is {monthly['learning_confidence']}% based on current data coverage.")
        return {"status":"ok","generated_at":end.isoformat(),"person_id":person_id,"summary":{"today_events":daily["total_events"],"week_events":weekly["total_events"],"month_events":monthly["total_events"],"habit_score":monthly["habit_score"],"learning_confidence":monthly["learning_confidence"],"monthly_trend":monthly["trend"]},"heatmap":{"days":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],"hours":list(range(24)),"values":heatmap},"insights":insights,"daily":daily,"weekly":weekly,"monthly":monthly}
