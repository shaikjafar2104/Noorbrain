from __future__ import annotations
class ToolEngine:
    def list(self): return [{'name':x} for x in ['automation_diagnostics','device_stats','list_devices']]
    def execute(self,name,payload):
        if name=='list_devices':
            from services.automation.manager import device_manager
            return {'status':'ok','devices':[x.model_dump(mode='json') for x in device_manager.list_devices()]}
        if name=='device_stats':
            from services.automation.manager import device_manager
            return {'status':'ok','stats':device_manager.stats()}
        if name=='automation_diagnostics':
            from services.automation.diagnostics import automation_diagnostics
            return automation_diagnostics.snapshot()
        raise KeyError(name)
tool_engine=ToolEngine()
