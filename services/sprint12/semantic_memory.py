from __future__ import annotations
import re, math
from collections import Counter
from .memory_v2 import memory_v2
TOK=re.compile(r'[a-zA-Z0-9_]+')
def vec(s): return Counter(x.lower() for x in TOK.findall(s))
def sim(a,b):
    keys=set(a)|set(b); d=sum(a[k]*b[k] for k in keys); na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values())); return 0.0 if not na or not nb else d/(na*nb)
class SemanticMemory:
    def search(self,q,session_id=None,limit=10):
        items=memory_v2.store.read(); qv=vec(q)
        if session_id: items=[x for x in items if x.get('session_id')==session_id]
        out=[]
        for x in items:
            s=sim(qv,vec(str(x.get('content') or '')))
            if s>0: out.append({**x,'score':round(s,4)})
        return sorted(out,key=lambda x:x['score'],reverse=True)[:limit]
    def summarize(self,session_id):
        items=memory_v2.history(session_id,100); users=[x for x in items if x.get('role')=='user']
        return {'session_id':session_id,'message_count':len(items),'user_message_count':len(users),'summary':f'Session contains {len(items)} messages.'}
semantic_memory=SemanticMemory()
