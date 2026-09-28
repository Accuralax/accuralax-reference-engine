from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any

from .it_asset_management import ITAsset
from .it_service_management import ITTicket


class ITOperationalStore:
    """Durable local store for IT tickets and CMDB assets."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent.parent.parent / "data" / "it_operations.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        conn = self._connect()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                asset_type TEXT NOT NULL,
                name TEXT NOT NULL,
                owner TEXT,
                location TEXT,
                status TEXT NOT NULL,
                serial_number TEXT,
                warranty_until TEXT,
                parent_asset_id TEXT,
                related_asset_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                reference_id TEXT NOT NULL,
                request TEXT NOT NULL,
                ticket_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_agent TEXT,
                sla_target_minutes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                verified INTEGER NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ticket_assets (
                ticket_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                PRIMARY KEY(ticket_id, asset_id)
            )""")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ITOperationalStore._safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        return value

    def save_asset(self, asset: ITAsset) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO assets
                (asset_id,asset_type,name,owner,location,status,serial_number,warranty_until,parent_asset_id,related_asset_ids,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (asset.asset_id, asset.asset_type, asset.name, asset.owner, asset.location, asset.status,
                 asset.serial_number, asset.warranty_until, asset.parent_asset_id,
                 json.dumps(asset.related_asset_ids), asset.created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def save_ticket(self, ticket: ITTicket) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO tickets
                (ticket_id,reference_id,request,ticket_type,priority,status,assigned_agent,sla_target_minutes,created_at,verified)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (ticket.ticket_id, ticket.reference_id, ticket.request, ticket.ticket_type, ticket.priority,
                 ticket.status, ticket.assigned_agent, ticket.sla_target_minutes, ticket.created_at, int(ticket.verified)),
            )
            conn.commit()
        finally:
            conn.close()

    def link_ticket_asset(self, ticket_id: str, asset_id: str) -> None:
        conn = self._connect()
        try:
            conn.execute("INSERT OR IGNORE INTO ticket_assets(ticket_id,asset_id) VALUES(?,?)", (ticket_id, asset_id))
            conn.commit()
        finally:
            conn.close()

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def ticket_assets(self, ticket_id: str) -> list[str]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT asset_id FROM ticket_assets WHERE ticket_id=? ORDER BY asset_id", (ticket_id,)).fetchall()
            return [row["asset_id"] for row in rows]
        finally:
            conn.close()

    def counts(self) -> dict[str, int]:
        conn = self._connect()
        try:
            return {
                "assets": int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]),
                "tickets": int(conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]),
                "ticket_asset_links": int(conn.execute("SELECT COUNT(*) FROM ticket_assets").fetchone()[0]),
            }
        finally:
            conn.close()

    def snapshot(self) -> dict[str, Any]:
        return {
            "durable": True,
            "entities": ["assets", "tickets", "ticket_assets"],
            "credential_storage": False,
            "local_only": True,
            "audit_events": "separate_it_event_store",
        }
