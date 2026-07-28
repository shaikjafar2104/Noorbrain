"""Transparent, deterministic predictions from NoorBrain learning events."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import exp
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _confidence(top: int, total: int, samples: int) -> float:
    if total <= 0: return 0.0
    purity = top / total
    evidence = 1.0 - exp(-samples / 12.0)
    return round(max(0.0, min(0.99, purity * evidence)), 3)


class PredictionEngine:
    def __init__(self, store: Any) -> None: self.store = store

    def _events(self, *, person_id: Optional[str], days: int = 60, limit: int = 5000) -> List[Dict[str, Any]]:
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = self.store.list_events(limit=limit, person_id=person_id, start_at=start)
        return sorted(events, key=lambda e: (e["occurred_at"], e["id"]))

    def next_room(self, *, current_room: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        events = [e for e in self._events(person_id=person_id) if e.get("room")]
        transitions: Counter[str] = Counter()
        for a, b in zip(events, events[1:]):
            if current_room and a.get("room") != current_room: continue
            if a.get("room") != b.get("room"): transitions[str(b["room"])] += 1
        if not transitions:
            overall = Counter(str(e["room"]) for e in events if e.get("room") != current_room)
            transitions = overall
        total = sum(transitions.values())
        if not transitions:
            return {"status":"insufficient_data","prediction":None,"confidence":0.0,"samples":0}
        room, count = transitions.most_common(1)[0]
        return {"status":"ok","prediction":room,"confidence":_confidence(count,total,total),"samples":total,"alternatives":[{"room":r,"count":c,"probability":round(c/total,3)} for r,c in transitions.most_common(5)]}

    def next_activity(self, *, person_id: Optional[str] = None, current_event_type: Optional[str] = None) -> Dict[str, Any]:
        events = self._events(person_id=person_id)
        counts: Counter[str] = Counter()
        for a,b in zip(events,events[1:]):
            if current_event_type and a.get("event_type") != current_event_type: continue
            counts[str(b["event_type"])] += 1
        if not counts: counts = Counter(str(e["event_type"]) for e in events)
        total=sum(counts.values())
        if not counts: return {"status":"insufficient_data","prediction":None,"confidence":0.0,"samples":0}
        activity,count=counts.most_common(1)[0]
        return {"status":"ok","prediction":activity,"confidence":_confidence(count,total,total),"samples":total,"alternatives":[{"event_type":k,"count":v,"probability":round(v/total,3)} for k,v in counts.most_common(5)]}

    def occupancy(self, *, room: str, at: Optional[datetime] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        target = at or datetime.now(timezone.utc)
        events=[e for e in self._events(person_id=person_id,days=90) if e.get("room")]
        same_slot=[e for e in events if _parse(e["occurred_at"]).weekday()==target.weekday() and abs(_parse(e["occurred_at"]).hour-target.hour)<=1]
        occupied=sum(1 for e in same_slot if e.get("room")==room)
        total=len(same_slot)
        probability=round(occupied/total,3) if total else 0.0
        return {"status":"ok" if total else "insufficient_data","room":room,"predicted_occupied":probability>=0.5,"probability":probability,"confidence":_confidence(max(occupied,total-occupied),total,total),"samples":total,"target_time":target.isoformat()}

    def reminder_time(self, *, event_type: str = "prayer_reminder", person_id: Optional[str] = None) -> Dict[str, Any]:
        events=[e for e in self._events(person_id=person_id,days=90) if e.get("event_type")==event_type]
        if not events: return {"status":"insufficient_data","event_type":event_type,"recommended_time":None,"confidence":0.0,"samples":0}
        minutes=[_parse(e["occurred_at"]).hour*60+_parse(e["occurred_at"]).minute for e in events]
        buckets=Counter((m//15)*15 for m in minutes); bucket,count=buckets.most_common(1)[0]
        return {"status":"ok","event_type":event_type,"recommended_time":f"{bucket//60:02d}:{bucket%60:02d}","window_minutes":15,"confidence":_confidence(count,len(events),len(events)),"samples":len(events)}

    def summary(self, *, person_id: Optional[str] = None) -> Dict[str, Any]:
        return {"status":"ok","service":"prediction","sprint":"9.2","person_id":person_id,"next_room":self.next_room(person_id=person_id),"next_activity":self.next_activity(person_id=person_id),"reminder":self.reminder_time(person_id=person_id)}
