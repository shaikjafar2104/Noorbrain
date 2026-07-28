"""Explainable anomaly and missed-routine detection."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

def _parse(v:str)->datetime:
    d=datetime.fromisoformat(v.replace("Z","+00:00")); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

class AnomalyEngine:
    def __init__(self,store:Any)->None:self.store=store
    def recent(self,hours:int=24,person_id:Optional[str]=None)->List[Dict[str,Any]]:
        start=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat()
        return self.store.list_events(limit=5000,person_id=person_id,start_at=start)
    def scan(self,*,hours:int=24,person_id:Optional[str]=None)->Dict[str,Any]:
        now=datetime.now(timezone.utc); recent=self.recent(hours,person_id); baseline=self.store.list_events(limit=5000,person_id=person_id,start_at=(now-timedelta(days=60)).isoformat(),end_at=(now-timedelta(hours=hours)).isoformat())
        type_counts=Counter(e["event_type"] for e in baseline); room_counts=Counter(e.get("room") for e in baseline if e.get("room")); anomalies=[]
        for e in recent:
            reasons=[]
            if type_counts[e["event_type"]] < 2: reasons.append("rare_event_type")
            if e.get("room") and room_counts[e["room"]] < 2: reasons.append("rare_room")
            dt=_parse(e["occurred_at"])
            comparable=[_parse(x["occurred_at"]).hour for x in baseline if x["event_type"]==e["event_type"]]
            if len(comparable)>=5 and all(abs(dt.hour-h)>3 for h in comparable): reasons.append("unusual_time")
            if reasons: anomalies.append({"event_id":e["id"],"event_type":e["event_type"],"room":e.get("room"),"occurred_at":e["occurred_at"],"reasons":reasons,"severity":"medium" if len(reasons)>1 else "low"})
        return {"status":"ok","window_hours":hours,"events_scanned":len(recent),"baseline_events":len(baseline),"anomaly_count":len(anomalies),"anomalies":anomalies[:100]}
    def missed_routines(self,*,days:int=14,person_id:Optional[str]=None)->Dict[str,Any]:
        now=datetime.now(timezone.utc); events=self.store.list_events(limit=10000,person_id=person_id,start_at=(now-timedelta(days=days*2)).isoformat())
        historic=[e for e in events if _parse(e["occurred_at"]) < now-timedelta(days=days)]; recent=[e for e in events if _parse(e["occurred_at"]) >= now-timedelta(days=days)]
        h=Counter(e["event_type"] for e in historic); r=Counter(e["event_type"] for e in recent); missed=[]
        for event_type,count in h.items():
            expected=max(1,round(count)); actual=r[event_type]
            if count>=3 and actual < expected*0.4: missed.append({"event_type":event_type,"historical_count":count,"recent_count":actual,"status":"possibly_missed"})
        return {"status":"ok","comparison_days":days,"missed_count":len(missed),"missed_routines":missed}
