from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .final_qa import automation_final_qa

class Sprint11Completion:
    def __init__(self):
        self.project_root=Path(__file__).resolve().parents[2]
        self.marker=self.project_root/'data'/'sprint11_complete.json'
    def status(self)->dict[str,Any]:
        qa=automation_final_qa.run()
        return {'status':'complete' if qa['status']=='PASS' else 'incomplete','sprint':'11','title':'Smart Home Automation Platform','packs':{'pack1':'complete','pack2':'complete','pack3':'complete','pack4':'complete','pack5':'complete' if qa['status']=='PASS' else 'qa_failed'},'qa':qa,'ready_for_sprint12':qa['status']=='PASS'}
    def write_marker(self)->dict[str,Any]:
        payload=self.status(); payload['recorded_at']=datetime.now(timezone.utc).isoformat()
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return payload

sprint11_completion=Sprint11Completion()
