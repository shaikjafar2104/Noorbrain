"""Daily, weekly, and monthly learning patterns for NoorBrain."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .storage import LearningStore


def _parse_day(day: Optional[str]) -> date:
    return date.fromisoformat(day) if day else datetime.now(timezone.utc).date()


def _bounds_for_day(day: date) -> Tuple[str, str]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start.isoformat(), (start + timedelta(days=1)).isoformat()


def _bounds_for_week(week_start: Optional[str]) -> Tuple[date, str, str]:
    if week_start:
        start_day = date.fromisoformat(week_start)
    else:
        today = datetime.now(timezone.utc).date()
        start_day = today - timedelta(days=today.weekday())
    start = datetime.combine(start_day, time.min, tzinfo=timezone.utc)
    return start_day, start.isoformat(), (start + timedelta(days=7)).isoformat()


def _month_bounds(month: Optional[str]) -> Tuple[date, date, str, str]:
    if month:
        try:
            start_day = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise ValueError("month must be YYYY-MM") from exc
    else:
        start_day = datetime.now(timezone.utc).date().replace(day=1)
    end_day = date(start_day.year + (1 if start_day.month == 12 else 0), 1 if start_day.month == 12 else start_day.month + 1, 1)
    start = datetime.combine(start_day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_day, time.min, tzinfo=timezone.utc)
    return start_day, end_day, start.isoformat(), end.isoformat()


class DailyPatternBuilder:
    def __init__(self, store: LearningStore) -> None:
        self.store = store

    def build(self, day: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        target = _parse_day(day)
        start_at, end_at = _bounds_for_day(target)
        clauses, values = ["occurred_at >= ?", "occurred_at < ?"], [start_at, end_at]
        if person_id:
            clauses.append("person_id = ?"); values.append(person_id)
        where = " AND ".join(clauses)
        total = self.store.aggregate(f"SELECT COUNT(*) AS count FROM learning_events WHERE {where}", values)[0]
        hourly_rows = self.store.aggregate(f"SELECT CAST(strftime('%H', occurred_at) AS INTEGER) AS hour, COUNT(*) AS count FROM learning_events WHERE {where} GROUP BY hour ORDER BY hour", values)
        room_rows = self.store.aggregate(f"SELECT COALESCE(room, 'unknown') AS room, COUNT(*) AS count FROM learning_events WHERE {where} GROUP BY COALESCE(room, 'unknown') ORDER BY count DESC, room", values)
        type_rows = self.store.aggregate(f"SELECT event_type, COUNT(*) AS count FROM learning_events WHERE {where} GROUP BY event_type ORDER BY count DESC, event_type", values)
        hourly = {str(hour): 0 for hour in range(24)}
        for row in hourly_rows: hourly[str(int(row["hour"]))] = int(row["count"])
        active = [(int(hour), count) for hour, count in hourly.items() if count]
        return {"status":"ok","day":target.isoformat(),"timezone":"UTC","person_id":person_id,"total_events":int(total["count"]),"hourly_activity":hourly,"peak_hour":max(active,key=lambda x:(x[1],-x[0]))[0] if active else None,"rooms":room_rows,"event_types":type_rows}


class WeeklyPatternBuilder:
    def __init__(self, store: LearningStore) -> None: self.store = store

    def build(self, week_start: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        start_day, start_at, end_at = _bounds_for_week(week_start)
        clauses, values = ["occurred_at >= ?", "occurred_at < ?"], [start_at, end_at]
        if person_id: clauses.append("person_id = ?"); values.append(person_id)
        rows = self.store.aggregate(f"SELECT occurred_at,event_type,COALESCE(room,'unknown') AS room FROM learning_events WHERE {' AND '.join(clauses)} ORDER BY occurred_at", values)
        names=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        counts=[0]*7; rooms=defaultdict(int); types=defaultdict(int); prayer=0
        for row in rows:
            wd=datetime.fromisoformat(str(row["occurred_at"]).replace("Z","+00:00")).weekday(); counts[wd]+=1
            rooms[str(row["room"])]+=1; et=str(row["event_type"]); types[et]+=1
            if "prayer" in et.lower() or "salah" in et.lower(): prayer+=1
        daily=[{"weekday":i,"day":names[i],"count":counts[i]} for i in range(7)]
        active=sum(1 for c in counts if c)
        return {"status":"ok","week_start":start_day.isoformat(),"week_end":(start_day+timedelta(days=6)).isoformat(),"timezone":"UTC","person_id":person_id,"total_events":len(rows),"daily_activity":daily,"peak_day":max(daily,key=lambda x:x["count"]) if rows else None,"weekday_events":sum(counts[:5]),"weekend_events":sum(counts[5:]),"weekday_daily_average":round(sum(counts[:5])/5,2),"weekend_daily_average":round(sum(counts[5:])/2,2),"prayer_events":prayer,"active_days":active,"consistency_score":round(active/7*100,2),"rooms":[{"room":k,"count":v} for k,v in sorted(rooms.items(),key=lambda x:(-x[1],x[0]))],"event_types":[{"event_type":k,"count":v} for k,v in sorted(types.items(),key=lambda x:(-x[1],x[0]))]}


class MonthlyPatternBuilder:
    """Builds long-term monthly habits, trends, and confidence."""
    def __init__(self, store: LearningStore) -> None: self.store = store

    def build(self, month: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        start_day, end_day, start_at, end_at = _month_bounds(month)
        clauses, values = ["occurred_at >= ?", "occurred_at < ?"], [start_at, end_at]
        if person_id: clauses.append("person_id = ?"); values.append(person_id)
        where=" AND ".join(clauses)
        rows=self.store.aggregate(f"SELECT occurred_at,event_type,COALESCE(room,'unknown') AS room FROM learning_events WHERE {where} ORDER BY occurred_at",values)
        days=(end_day-start_day).days; daily={str(i):0 for i in range(1,days+1)}; hours={str(i):0 for i in range(24)}
        rooms=defaultdict(int); types=defaultdict(int); weekday=0; weekend=0
        for row in rows:
            moment=datetime.fromisoformat(str(row["occurred_at"]).replace("Z","+00:00")); daily[str(moment.day)]+=1; hours[str(moment.hour)]+=1
            rooms[str(row["room"])]+=1; types[str(row["event_type"])]+=1
            if moment.weekday()<5: weekday+=1
            else: weekend+=1
        active_days=sum(1 for count in daily.values() if count); total=len(rows); coverage=active_days/days if days else 0
        # Confidence rewards data volume and calendar coverage but never claims certainty.
        volume=min(1.0,total/100.0); confidence=round((coverage*0.65+volume*0.35)*100,2)
        habit_score=round((coverage*0.7+min(1.0,total/max(days,1))*0.3)*100,2)
        first_half=sum(v for k,v in daily.items() if int(k)<=days/2); second_half=total-first_half
        if second_half>first_half*1.1: trend="increasing"
        elif first_half>second_half*1.1: trend="decreasing"
        else: trend="stable"
        peak_hour=max(hours,key=lambda k:(hours[k],-int(k))) if total else None
        top_room=max(rooms,key=rooms.get) if rooms else None; top_type=max(types,key=types.get) if types else None
        return {"status":"ok","month":start_day.strftime("%Y-%m"),"timezone":"UTC","person_id":person_id,"days_in_month":days,"total_events":total,"active_days":active_days,"daily_average":round(total/days,2),"calendar_coverage_percent":round(coverage*100,2),"habit_score":habit_score,"learning_confidence":confidence,"trend":trend,"first_half_events":first_half,"second_half_events":second_half,"peak_hour":int(peak_hour) if peak_hour is not None else None,"top_room":top_room,"top_event_type":top_type,"weekday_events":weekday,"weekend_events":weekend,"daily_activity":[{"day":int(k),"count":v} for k,v in daily.items()],"hourly_activity":hours,"rooms":[{"room":k,"count":v} for k,v in sorted(rooms.items(),key=lambda x:(-x[1],x[0]))],"event_types":[{"event_type":k,"count":v} for k,v in sorted(types.items(),key=lambda x:(-x[1],x[0]))]}
