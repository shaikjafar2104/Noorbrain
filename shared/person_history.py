import time
from shared.logger import logger
class PersonHistory:
    def __init__(self): self.history={}
    def update(self,detections):
        now=time.time()
        for detection in detections:
            if detection.get('label')!='person': continue
            pid=detection.get('id','person')
            zone=detection.get('zone','Unknown')
            events=self.history.setdefault(pid,[])
            if not events or events[-1]['zone']!=zone:
                events.append({'zone':zone,'time':now})
                logger.info(f'PersonHistory : {pid} -> {zone}')
    def path(self,pid): return list(self.history.get(pid,[]))
    def snapshot(self): return {k:list(v) for k,v in self.history.items()}
person_history=PersonHistory()
