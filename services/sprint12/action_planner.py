from .tool_engine import tool_engine
class ActionPlanner:
    def plan(self,intent,context=None):
        t=intent.lower(); tool='list_devices' if 'list' in t and 'device' in t else ('device_stats' if 'device' in t else 'automation_diagnostics')
        return {'status':'planned','intent':intent,'tool':tool,'arguments':{},'requires_approval':False}
    def execute(self,plan): return tool_engine.execute(plan['tool'],plan.get('arguments',{}))
action_planner=ActionPlanner()
