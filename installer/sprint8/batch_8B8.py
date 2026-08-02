from pathlib import Path
import json
P=Path.home()/"Projects"/"NoorBrain"; store=P/"data/routine_intelligence_v8.json"
default={"version":1,"activities":[],"routines":[],"habits":[],"predictions":[],"settings":{}}
try:data=json.loads(store.read_text(encoding="utf-8")) if store.exists() else default
except Exception:data=default
data.setdefault("settings",{}); data["settings"].update({'weekly_summary': True})
store.parent.mkdir(parents=True,exist_ok=True); store.write_text(json.dumps(data,indent=2),encoding="utf-8")
print("SPRINT 8B8 WEEKLY SUMMARY PASS")
