from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any


class ITPersistentStore:
    """Durable local ITSM event store. Secrets are filtered before persistence."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent.parent.parent / "data" / "it_service.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS it_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_id TEXT NOT NULL,
                    ticket_id TEXT,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_it_events_reference ON it_events(reference_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_it_events_ticket ON it_events(ticket_id)")
        finally:
            conn.close()

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ITPersistentStore._safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ITPersistentStore._safe(v) for v in value]
        return value

    def record(self, reference_id: str, event_type: str, details: dict[str, Any] | None = None, *, ticket_id: str | None = None) -> int:
        safe = self._safe(details or {})
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO it_events(reference_id,ticket_id,event_type,details_json) VALUES(?,?,?,?)",
                (reference_id, ticket_id, event_type, json.dumps(safe, sort_keys=True, default=str)),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    def list_events(self, reference_id: str, *, ticket_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            if ticket_id:
                rows = conn.execute(
                    "SELECT * FROM it_events WHERE reference_id=? AND ticket_id=? ORDER BY event_id",
                    (reference_id, ticket_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM it_events WHERE reference_id=? ORDER BY event_id",
                    (reference_id,),
                ).fetchall()
        finally:
            conn.close()
        return [
            {
                "event_id": row["event_id"],
                "reference_id": row["reference_id"],
                "ticket_id": row["ticket_id"],
                "event_type": row["event_type"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def count(self) -> int:
        conn = self._connect()
        try:
            return int(conn.execute("SELECT COUNT(*) FROM it_events").fetchone()[0])
        finally:
            conn.close()

    def close(self) -> None:
        """Compatibility hook; connections are opened per operation and closed immediately."""
        return None
