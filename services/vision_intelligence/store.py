from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

def utc_now(): return datetime.now(timezone.utc).isoformat()

class VisionEventStore:
    def __init__(self):
        project = Path(__file__).resolve().parents[2]
        self.path = project/'data'/'vision_intelligence_events.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists(): self._write({'schema_version':1,'events':[]})
    def _read(self):
        with self.lock: data=json.loads(self.path.read_text(encoding='utf-8'))
        data.setdefault('schema_version',1); data.setdefault('events',[]); return data
    def _write(self,data):
        with self.lock:
            fd,tmp=tempfile.mkstemp(prefix='vision-',suffix='.tmp',dir=str(self.path.parent))
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as h:
                    json.dump(data,h,indent=2,ensure_ascii=False); h.write('\n'); h.flush(); os.fsync(h.fileno())
                os.replace(tmp,self.path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
    def add(self,event:dict[str,Any]):
        data=self._read(); item={'id':uuid4().hex,'created_at':utc_now(),**event}; data['events'].append(item); data['events']=data['events'][-5000:]; self._write(data); return item
    def list(self,limit=100,event_type=None,zone=None):
        items=list(reversed(self._read()['events']))
        if event_type: items=[e for e in items if str(e.get('event_type','')).casefold()==event_type.casefold()]
        if zone: items=[e for e in items if str(e.get('zone') or '').casefold()==zone.casefold()]
        return items[:limit]
    def summary(self):
        items=self._read()['events']; by_type={}; by_zone={}
        for e in items:
            t=str(e.get('event_type') or 'unknown'); z=str(e.get('zone') or 'unassigned')
            by_type[t]=by_type.get(t,0)+1; by_zone[z]=by_zone.get(z,0)+1
        return {'status':'ok','total_events':len(items),'by_type':by_type,'by_zone':by_zone}
    def clear(self):
        data=self._read(); n=len(data['events']); data['events']=[]; self._write(data); return n
vision_event_store=VisionEventStore()
