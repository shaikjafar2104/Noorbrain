from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()
class ProfileStore:
    def __init__(self):
        root=Path(__file__).resolve().parents[2]; self.path=root/'data'/'sprint12_profiles.json'; self.path.parent.mkdir(parents=True,exist_ok=True); self.lock=RLock()
        if not self.path.exists(): self._write([])
    def _read(self): return json.loads(self.path.read_text()).get('profiles',[])
    def _write(self,items):
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix='profiles-',suffix='.tmp')
        try:
            with os.fdopen(fd,'w') as f: json.dump({'schema_version':1,'profiles':items},f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def list(self): return self._read()
    def create(self,p):
        name=str(p.get('name') or '').strip()
        if not name: raise ValueError('Profile name is required.')
        item={'id':uuid4().hex,'name':name,'language':p.get('language','en'),'preferences':p.get('preferences',{}),'permissions':p.get('permissions',[]),'created_at':now(),'updated_at':now()}
        items=self.list(); items.append(item); self._write(items); return item
    def update(self,i,p):
        items=self.list(); idx=next((n for n,x in enumerate(items) if x['id']==i),None)
        if idx is None: raise KeyError(i)
        for k,v in p.items():
            if k not in {'id','created_at'}: items[idx][k]=v
        items[idx]['updated_at']=now(); self._write(items); return items[idx]
    def delete(self,i):
        items=self.list(); rem=[x for x in items if x['id']!=i]
        if len(rem)==len(items): return False
        self._write(rem); return True
profile_store=ProfileStore()
