from __future__ import annotations
import json,time,uuid,statistics
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from typing import Any
from fastapi import APIRouter,Body,HTTPException

router=APIRouter(prefix="/api/routine-intelligence-v8",tags=["Routine Intelligence v8"])
ROOT=Path(__file__).resolve().parents[2]
STORE=ROOT/"data"/"routine_intelligence_v8.json"
DEFAULT={"version":1,"activities":[],"routines":[],"habits":[],"predictions":[],"settings":{"timeline_enabled":True,"activity_tracking":True,"habit_detection":True,"prediction_enabled":True,"minimum_occurrences":3,"prediction_window_minutes":90}}

def read_store():
    STORE.parent.mkdir(parents=True,exist_ok=True)
    if not STORE.exists():
        write_store(DEFAULT.copy()); return json.loads(json.dumps(DEFAULT))
    try:data=json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:data={}
    result=json.loads(json.dumps(DEFAULT))
    if isinstance(data,dict):result.update(data)
    for k in ("activities","routines","habits","predictions"):result.setdefault(k,[])
    result.setdefault("settings",DEFAULT["settings"].copy())
    return result

def write_store(data):
    STORE.parent.mkdir(parents=True,exist_ok=True)
    tmp=STORE.with_suffix(".tmp"); tmp.write_text(json.dumps(data,indent=2),encoding="utf-8"); tmp.replace(STORE)

def minute_of_day(ts):
    d=datetime.fromtimestamp(ts); return d.hour*60+d.minute

def day_key(ts): return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

@router.get("/health")
def health():
    d=read_store(); return {"status":"healthy","service":"routine_intelligence_v8","version":"8.2.0","activities":len(d["activities"]),"routines":len(d["routines"]),"habits":len(d["habits"])}

@router.get("/state")
def state(): return {"status":"ok","routine_intelligence":read_store()}

@router.get("/timeline")
def timeline(days:int=7):
    d=read_store(); cutoff=int((datetime.now()-timedelta(days=max(1,min(days,90)))).timestamp())
    items=[x for x in d["activities"] if int(x.get("timestamp",0))>=cutoff]
    items.sort(key=lambda x:int(x.get("timestamp",0)),reverse=True)
    return {"status":"ok","activities":items}

@router.post("/activities")
def add_activity(payload:dict[str,Any]=Body(...)):
    name=str(payload.get("name") or "").strip()
    if not name: raise HTTPException(status_code=422,detail="Activity name is required.")
    d=read_store()
    item={"id":uuid.uuid4().hex[:12],"name":name,"category":str(payload.get("category") or "general"),"source":str(payload.get("source") or "manual"),"room":str(payload.get("room") or ""),"person":str(payload.get("person") or ""),"metadata":payload.get("metadata") or {},"timestamp":int(payload.get("timestamp") or time.time())}
    d["activities"].append(item); d["activities"]=d["activities"][-5000:]; write_store(d)
    return {"status":"created","activity":item}

@router.post("/routines")
def add_routine(payload:dict[str,Any]=Body(...)):
    name=str(payload.get("name") or "").strip()
    if not name: raise HTTPException(status_code=422,detail="Routine name is required.")
    d=read_store(); item={"id":uuid.uuid4().hex[:12],"name":name,"days":payload.get("days") or [],"time":str(payload.get("time") or ""),"actions":payload.get("actions") or [],"enabled":bool(payload.get("enabled",True))}
    d["routines"].append(item); write_store(d); return {"status":"created","routine":item}

@router.post("/schedule/optimize")
def optimize_schedule():
    d=read_store(); grouped=defaultdict(list)
    for x in d["activities"]: grouped[str(x.get("name") or "activity")].append(minute_of_day(int(x.get("timestamp",0))))
    result=[]
    for name,vals in grouped.items():
        if len(vals)<2: continue
        avg=int(round(statistics.mean(vals)))
        result.append({"name":name,"suggested_time":f"{avg//60:02d}:{avg%60:02d}","samples":len(vals)})
    return {"status":"ok","suggestions":result}

@router.post("/habits/detect")
def detect_habits():
    d=read_store(); minimum=int(d["settings"].get("minimum_occurrences",3)); grouped=defaultdict(list)
    for x in d["activities"]: grouped[(str(x.get("name")),str(x.get("room")))].append(x)
    habits=[]
    for (name,room),items in grouped.items():
        if len(items)<minimum: continue
        vals=[minute_of_day(int(x["timestamp"])) for x in items]; avg=int(round(statistics.mean(vals)))
        spread=int(round(statistics.pstdev(vals))) if len(vals)>1 else 0
        habits.append({"id":f"habit-{abs(hash((name,room)))%10000000}","name":name,"room":room,"occurrences":len(items),"expected_time":f"{avg//60:02d}:{avg%60:02d}","time_spread_minutes":spread,"confidence":round(min(1.0,len(items)/max(minimum*2,1)),3)})
    d["habits"]=habits; write_store(d); return {"status":"completed","habits":habits}

@router.get("/patterns")
def patterns():
    d=read_store()
    return {"status":"ok","categories":dict(Counter(str(x.get("category") or "general") for x in d["activities"])),"rooms":dict(Counter(str(x.get("room") or "unknown") for x in d["activities"])),"total":len(d["activities"])}

@router.get("/summary/daily")
def daily_summary(date:str=""):
    d=read_store(); target=date or datetime.now().strftime("%Y-%m-%d"); items=[x for x in d["activities"] if day_key(int(x.get("timestamp",0)))==target]
    return {"status":"ok","date":target,"count":len(items),"categories":dict(Counter(str(x.get("category") or "general") for x in items)),"activities":items[-50:]}

@router.get("/summary/weekly")
def weekly_summary():
    d=read_store(); cutoff=int((datetime.now()-timedelta(days=7)).timestamp()); items=[x for x in d["activities"] if int(x.get("timestamp",0))>=cutoff]
    return {"status":"ok","count":len(items),"days":dict(Counter(day_key(int(x.get("timestamp",0))) for x in items)),"top_activities":Counter(str(x.get("name")) for x in items).most_common(10)}

@router.post("/predict")
def predict():
    d=read_store(); now=datetime.now().hour*60+datetime.now().minute; window=int(d["settings"].get("prediction_window_minutes",90)); preds=[]
    for h in d["habits"]:
        hh,mm=[int(x) for x in h["expected_time"].split(":")]; expected=hh*60+mm; delta=expected-now
        if delta<0: delta+=1440
        if delta<=window: preds.append({"id":uuid.uuid4().hex[:12],"habit_id":h["id"],"name":h["name"],"room":h.get("room",""),"minutes_until":delta,"confidence":h.get("confidence",0),"created_at":int(time.time())})
    d["predictions"]=preds; write_store(d); return {"status":"completed","predictions":preds}

@router.post("/ai-routine")
def ai_routine():
    d=read_store()
    if not d["habits"]: detect_habits(); d=read_store()
    created=[]; existing={str(x.get("name")) for x in d["routines"]}
    for h in d["habits"]:
        name=f"AI: {h['name']}"
        if name in existing: continue
        r={"id":uuid.uuid4().hex[:12],"name":name,"days":["mon","tue","wed","thu","fri","sat","sun"],"time":h["expected_time"],"actions":[{"type":"halo_suggestion","message":f"Your usual {h['name']} routine is coming up."}],"enabled":True,"source":"ai"}
        d["routines"].append(r); created.append(r)
    write_store(d); return {"status":"completed","created":created}

@router.post("/settings")
def update_settings(payload:dict[str,Any]=Body(...)):
    d=read_store(); d["settings"].update(payload); write_store(d); return {"status":"updated","settings":d["settings"]}
