from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ConversationEngine:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "voice.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    person_id TEXT,
                    room TEXT,
                    user_text TEXT NOT NULL,
                    assistant_text TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_turns_created ON voice_turns(created_at)")

    @staticmethod
    def _intent(text: str) -> str:
        normalized = text.lower().strip()
        if any(x in normalized for x in ("salam", "assalamu", "hello", "hi ")): return "greeting"
        if "health" in normalized or "status" in normalized: return "system_status"
        if "prayer" in normalized or "namaz" in normalized or "salah" in normalized: return "prayer"
        if "report" in normalized or "summary" in normalized: return "report"
        if "time" in normalized: return "time"
        return "general"


    def save_turn(self, user_text: str, assistant_text: str, intent: str, person_id: Optional[str] = None,
                  room: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO voice_turns(created_at, person_id, room, user_text, assistant_text, intent, metadata_json) VALUES(?,?,?,?,?,?,?)",
                (created_at, person_id, room, user_text, assistant_text, intent, json.dumps(metadata or {})),
            )
            turn_id = int(cursor.lastrowid)
        return {"status": "ok", "turn_id": turn_id, "intent": intent, "input": user_text,
                "response": assistant_text, "person_id": person_id, "room": room, "created_at": created_at}

    def reply(self, text: str, person_id: Optional[str] = None, room: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        clean = " ".join(text.strip().split())
        intent = self._intent(clean)
        now = datetime.now().astimezone()
        if intent == "greeting":
            response = "Wa alaikum assalam. How can I help you?"
        elif intent == "system_status":
            response = "NoorBrain voice service is running. Open the health dashboard for full system details."
        elif intent == "prayer":
            response = "I can help with prayer reminders. Prayer-time integration will use your configured location and schedule."
        elif intent == "report":
            response = "Your AI reports are available through the NoorBrain reports dashboard."
        elif intent == "time":
            response = f"The current local time is {now.strftime('%I:%M %p')}."
        else:
            response = "I heard you. The local command router is active, and advanced language-model integration can be connected next."
        return self.save_turn(clean, response, intent, person_id, room, metadata)

    def history(self, limit: int = 50) -> Dict[str, Any]:
        limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM voice_turns ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        turns = []
        for row in rows:
            item = dict(row)
            try: item["metadata"] = json.loads(item.pop("metadata_json"))
            except Exception: item["metadata"] = {}; item.pop("metadata_json", None)
            turns.append(item)
        return {"status": "ok", "count": len(turns), "turns": turns}
