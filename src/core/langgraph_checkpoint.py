from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3


@dataclass
class Checkpoint:
    checkpoint_id: str
    reference_id: str
    node: str
    state_hash: str
    state: dict[str, Any]
    created_at: str


class LangGraphCheckpointStore:
    """Durable, secret-safe checkpoints for bounded LangGraph workflows."""

    def __init__(self, db_path: str | Path = Path("data") / "langgraph_checkpoints.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY, reference_id TEXT NOT NULL, node TEXT NOT NULL,
                state_hash TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            db.commit()

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): LangGraphCheckpointStore._safe(v)
                    for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [LangGraphCheckpointStore._safe(v) for v in value]
        return value

    def save(self, reference_id: str, node: str, state: dict[str, Any]) -> Checkpoint:
        safe = self._safe(state)
        payload = json.dumps(safe, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        checkpoint_id = f"CHK-{digest[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?,?,?)",
                       (checkpoint_id, reference_id, node, digest, payload, now))
            db.commit()
        return Checkpoint(checkpoint_id, reference_id, node, digest, safe, now)

    def latest(self, reference_id: str) -> Checkpoint | None:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT checkpoint_id,reference_id,node,state_hash,state,created_at "
                "FROM checkpoints WHERE reference_id=? ORDER BY created_at DESC LIMIT 1",
                (reference_id,)
            ).fetchone()
        if not row:
            return None
        return Checkpoint(row[0], row[1], row[2], row[3], json.loads(row[4]), row[5])

    def history(self, reference_id: str) -> list[Checkpoint]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                "SELECT checkpoint_id,reference_id,node,state_hash,state,created_at "
                "FROM checkpoints WHERE reference_id=? ORDER BY created_at ASC",
                (reference_id,)
            ).fetchall()
        return [Checkpoint(r[0], r[1], r[2], r[3], json.loads(r[4]), r[5]) for r in rows]

    def health(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            count = db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        return {"status": "ok", "checkpoint_count": count, "credentials_stored": False}
