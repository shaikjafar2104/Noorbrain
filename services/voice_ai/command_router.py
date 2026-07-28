from __future__ import annotations
from datetime import datetime
from typing import Any, Dict


class LocalCommandRouter:
    def route(self, text: str) -> Dict[str, Any]:
        value = " ".join(text.lower().strip().split())
        if any(word in value for word in ("hello", "salam", "assalamu")):
            return {"handled": True, "intent": "greeting", "response": "Wa alaikum assalam. How can I help you?"}
        if "time" in value:
            return {"handled": True, "intent": "time", "response": f"The current local time is {datetime.now().astimezone().strftime('%I:%M %p')}."}
        if "report" in value or "summary" in value:
            return {"handled": True, "intent": "report", "response": "Your NoorBrain AI reports are ready in the reports dashboard."}
        if "health" in value or "status" in value:
            return {"handled": True, "intent": "system_status", "response": "NoorBrain is online. Use the health dashboard for detailed service status."}
        if "prayer" in value or "namaz" in value or "salah" in value:
            return {"handled": True, "intent": "prayer", "response": "Prayer reminder support is active and can use your configured schedule."}
        return {"handled": False, "intent": "general", "response": "I heard you. No local command matched this request."}
