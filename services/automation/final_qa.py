from __future__ import annotations
import time
from typing import Any
from .backup_restore import automation_backup_manager
from .diagnostics import automation_diagnostics
from .esp32_registry import esp32_registry
from .group_manager import group_manager
from .manager import device_manager
from .mqtt_service import mqtt_service
from .routine_scheduler import routine_scheduler
from .rule_engine import rule_engine
from .scene_manager import scene_manager

class AutomationFinalQA:
    def run(self) -> dict[str, Any]:
        started=time.perf_counter(); checks=[]
        def check(name, fn):
            try:
                result=fn(); passed=bool(result)
                checks.append({'name':name,'status':'PASS' if passed else 'FAIL','detail':result})
            except Exception as exc:
                checks.append({'name':name,'status':'FAIL','detail':f'{type(exc).__name__}: {exc}'})
        check('device_storage', lambda: device_manager.storage.integrity_check()['status']=='ok')
        check('automation_diagnostics', lambda: automation_diagnostics.snapshot()['status'] in {'healthy','degraded'})
        check('backup_validation', lambda: automation_backup_manager.validate_current()['status']=='ok')
        check('scene_storage', lambda: isinstance(scene_manager.list(), list))
        check('group_storage', lambda: isinstance(group_manager.list(), list))
        check('routine_storage', lambda: isinstance(routine_scheduler.list(), list))
        check('rule_storage', lambda: isinstance(rule_engine.list(), list))
        check('esp32_storage', lambda: isinstance(esp32_registry.list(), list))
        check('mqtt_status', lambda: 'available' in mqtt_service.status())
        passed=sum(1 for x in checks if x['status']=='PASS'); failed=len(checks)-passed
        return {'status':'PASS' if failed==0 else 'FAIL','passed':passed,'failed':failed,'checks':checks,'duration_ms':round((time.perf_counter()-started)*1000,2)}

automation_final_qa=AutomationFinalQA()
