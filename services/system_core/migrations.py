"""Small, dependency-free SQLite migration framework."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import time

from shared.logger import logger
from .version import DATABASE_SCHEMA_TARGET

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "noorbrain.db"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS = (
    Migration(
        version=1,
        name="system_metadata",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_events_time ON events(time)",
        ),
    ),
)


class MigrationManager:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @staticmethod
    def _ensure_table(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at REAL NOT NULL
            )
            """
        )
        conn.commit()

    def current_version(self) -> int:
        with self._connect() as conn:
            self._ensure_table(conn)
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()
            return int(row[0] if row else 0)

    def apply_pending(self) -> dict:
        applied: list[dict] = []
        with self._connect() as conn:
            self._ensure_table(conn)
            current = self.current_version()
            for migration in MIGRATIONS:
                if migration.version <= current:
                    continue
                logger.info(
                    "Applying database migration %s: %s",
                    migration.version,
                    migration.name,
                )
                try:
                    conn.execute("BEGIN")
                    for statement in migration.statements:
                        conn.execute(statement)
                    conn.execute(
                        "INSERT INTO schema_migrations(version,name,applied_at) VALUES (?,?,?)",
                        (migration.version, migration.name, time.time()),
                    )
                    conn.commit()
                    applied.append(
                        {"version": migration.version, "name": migration.name}
                    )
                    current = migration.version
                except Exception:
                    conn.rollback()
                    raise
        return {
            "status": "ok",
            "database": str(self.db_path),
            "current_version": self.current_version(),
            "target_version": DATABASE_SCHEMA_TARGET,
            "applied": applied,
        }

    def history(self) -> list[dict]:
        with self._connect() as conn:
            self._ensure_table(conn)
            rows = conn.execute(
                "SELECT version,name,applied_at FROM schema_migrations ORDER BY version"
            ).fetchall()
        return [
            {"version": int(v), "name": name, "applied_at": float(applied_at)}
            for v, name, applied_at in rows
        ]


migration_manager = MigrationManager()
