from collections import Counter, deque
from datetime import datetime
from pathlib import Path
import json, threading, time
class HabitEngine:
    def __init__(self,data_file="data/habit_memory.json",maximum_events=5000):
        self.data_file=Path(data_file); self.data_file.parent.mkdir(parents=True,exist_ok=True); self._events=deque(maxlen=maximum_events); self._lock=threading.RLock(); self._load()
    def _load(self):
        try:
            for e in json.loads(self.data_file.read_text()).get("events",[]): self._events.append(e)
        except Exception: pass
    def _save(self): self.data_file.write_text(json.dumps({"version":1,"events":list(self._events)},indent=2))
    def observe(self,event):
        if event.get("type") not in {"appeared","stayed","disappeared"}: return None
        ts=float(event.get("timestamp") or time.time()); dt=datetime.fromtimestamp(ts); rec={"type":event.get("type"),"person_id":event.get("person_id"),"timestamp":ts,"date":dt.strftime("%Y-%m-%d"),"hour":dt.hour,"weekday":dt.strftime("%A"),"duration":event.get("duration")}
        with self._lock: self._events.append(rec); self._save()
        return rec
    def summary(self,limit=100):
        events=list(self._events); a=[e for e in events if e.get("type")=="appeared"]; d=[e for e in events if e.get("type")=="disappeared"]; hc=Counter(e.get("hour") for e in a); wc=Counter(e.get("weekday") for e in a); durations=[float(e["duration"]) for e in d if isinstance(e.get("duration"),(int,float))]
        return {"status":"learning","mode":"offline_local","observations":len(events),"appearance_count":len(a),"disappearance_count":len(d),"most_common_arrival_hour":hc.most_common(1)[0][0] if hc else None,"most_active_weekday":wc.most_common(1)[0][0] if wc else None,"average_presence_seconds":round(sum(durations)/len(durations),1) if durations else None,"recent":list(reversed(events[-limit:]))}
    def clear(self):
        with self._lock: self._events.clear(); self._save()
        return {"status":"cleared"}
habit_engine=HabitEngine()
