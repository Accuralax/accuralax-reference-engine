from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any


@dataclass(frozen=True)
class PersistentRepairEvent:
    repair_id: str
    event: str
    status: str
    timestamp: str
    details: dict[str, Any]


class SQLiteRepairHistory:
    """Durable, local-only repair history with explicit SQLite lifecycle management."""

    def __init__(self, path: str | Path = "data/repairs.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repair_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repair_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repair_events_id ON repair_events(repair_id, id)")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
        blocked = ("password", "api_key", "apikey", "token", "secret", "card_number", "cvv")
        return {key: value for key, value in details.items()
                if not any(term in key.lower() for term in blocked)}

    def record(self, repair_id: str, event: str, status: str, details: dict[str, Any] | None = None) -> PersistentRepairEvent:
        timestamp = datetime.now(timezone.utc).isoformat()
        safe = self._safe_details(details or {})
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                "INSERT INTO repair_events(repair_id,event,status,timestamp,details_json) VALUES(?,?,?,?,?)",
                (repair_id, event, status, timestamp, json.dumps(safe, sort_keys=True)),
            )
            conn.commit()
        finally:
            conn.close()
        return PersistentRepairEvent(repair_id, event, status, timestamp, safe)

    def list(self, repair_id: str | None = None) -> list[PersistentRepairEvent]:
        query = "SELECT repair_id,event,status,timestamp,details_json FROM repair_events"
        args: tuple[Any, ...] = ()
        if repair_id is not None:
            query += " WHERE repair_id=?"
            args = (repair_id,)
        query += " ORDER BY id"
        conn = sqlite3.connect(self.path)
        try:
            rows = conn.execute(query, args).fetchall()
        finally:
            conn.close()
        return [PersistentRepairEvent(r[0], r[1], r[2], r[3], json.loads(r[4])) for r in rows]

    def count(self) -> int:
        conn = sqlite3.connect(self.path)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM repair_events").fetchone()[0])
        finally:
            conn.close()
