"""Thread-safe SQLite storage for NoorBrain events."""
import sqlite3
import threading
from pathlib import Path
from shared.logger import logger

DB_PATH = Path(__file__).resolve().parents[1] / "noorbrain.db"


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.init_db()

    def init_db(self):
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time REAL,
                    event TEXT,
                    zone TEXT,
                    source TEXT,
                    destination TEXT
                )
            """)
            self.conn.commit()
        logger.info(f"Database initialized: {self.db_path}")

    def add_event(self, time_val, event, zone=None, source=None, destination=None):
        try:
            with self._lock:
                self.conn.execute(
                    "INSERT INTO events (time,event,zone,source,destination) VALUES (?,?,?,?,?)",
                    (time_val, event, zone, source, destination),
                )
                self.conn.commit()
        except Exception as ex:
            logger.error(f"Database add_event error: {ex}")

    def recent_events(self, limit=20):
        try:
            with self._lock:
                cur = self.conn.execute(
                    "SELECT time,event,zone,source,destination FROM events ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                return cur.fetchall()
        except Exception as ex:
            logger.error(f"Database recent_events error: {ex}")
            return []

    def history_text(self, limit=50):
        lines = []
        for _, event, zone, source, destination in self.recent_events(limit):
            if event == "entered":
                lines.append(f"Person entered {zone}")
            elif event == "left":
                lines.append(f"Person left {zone}")
            elif event == "moved":
                lines.append(f"Person moved from {source} to {destination}")
        return "\n".join(lines)

    def close(self):
        with self._lock:
            self.conn.close()


database = Database()
