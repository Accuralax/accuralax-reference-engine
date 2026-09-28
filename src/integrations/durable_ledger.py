from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .execution import ExecutionReceipt


class SQLiteExecutionLedger:
    """Durable execution ledger for idempotency and audit receipts."""

    def __init__(self, path: str | Path = "data/executions.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS execution_receipts (
                idempotency_key TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL UNIQUE,
                system TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                attempt INTEGER NOT NULL,
                trace_json TEXT NOT NULL,
                error TEXT
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_created ON execution_receipts(created_at)")
            conn.commit()
        finally:
            conn.close()

    def get(self, key: str) -> ExecutionReceipt | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM execution_receipts WHERE idempotency_key = ?", (key,)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return ExecutionReceipt(
            row["execution_id"], row["idempotency_key"], row["system"], row["action"],
            row["status"], row["created_at"], row["attempt"], tuple(json.loads(row["trace_json"])), row["error"]
        )

    def record(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        existing = self.get(receipt.idempotency_key)
        if existing:
            return existing
        conn = self._connect()
        try:
            try:
                conn.execute(
                    "INSERT INTO execution_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (receipt.idempotency_key, receipt.execution_id, receipt.system, receipt.action,
                     receipt.status, receipt.created_at, receipt.attempt, json.dumps(list(receipt.trace)), receipt.error),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
        finally:
            conn.close()
        return self.get(receipt.idempotency_key) or receipt

    def count(self) -> int:
        conn = self._connect()
        try:
            return int(conn.execute("SELECT COUNT(*) FROM execution_receipts").fetchone()[0])
        finally:
            conn.close()
