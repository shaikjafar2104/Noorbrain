from __future__ import annotations
from typing import Any

def vision_snapshot()->dict[str,Any]:
    candidates=(('services.vision_engine.vision_engine','vision_engine'),('services.vision_engine','vision_engine'))
    errors=[]
    for module_name, attr in candidates:
        try:
            module=__import__(module_name,fromlist=[attr]); engine=getattr(module,attr); snap=engine.snapshot()
            if not isinstance(snap,dict): snap={'value':snap}
            people=snap.get('persons') or snap.get('people') or snap.get('detections') or []
            if not isinstance(people,list): people=[]
            count=snap.get('person_count') or snap.get('active_people') or len(people)
            return {'status':'healthy','person_count':int(count or 0),'persons':people,'zones':snap.get('zones') or [],'fps':snap.get('fps') or snap.get('average_fps') or snap.get('processing_fps'),'raw':snap}
        except Exception as exc: errors.append(f'{module_name}: {type(exc).__name__}: {exc}')
    return {'status':'unavailable','person_count':0,'persons':[],'zones':[],'fps':None,'raw':{},'errors':errors}
