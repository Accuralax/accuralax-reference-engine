from __future__ import annotations
from datetime import datetime, timezone
import sqlite3
import uuid


class WorkerLease:
    """Durable single-owner worker lease with heartbeat and stale recovery."""

    def __init__(self, db_path="data/worker_leases.sqlite3", lease_seconds=60):
        self.db_path = db_path
        self.lease_seconds = max(5, int(lease_seconds))
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS worker_leases (
                lease_id TEXT PRIMARY KEY, worker_code TEXT NOT NULL,
                owner_id TEXT NOT NULL, status TEXT NOT NULL,
                acquired_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL)""")
            c.commit()

    def _db(self):
        c = sqlite3.connect(self.db_path, timeout=15.0)
        c.execute("PRAGMA busy_timeout=15000")
        return c

    def acquire(self, worker_code, owner_id):
        now = datetime.now(timezone.utc)
        with self._db() as c:
            row = c.execute("SELECT lease_id,expires_at,owner_id FROM worker_leases WHERE worker_code=? AND status='active' ORDER BY acquired_at DESC LIMIT 1", (worker_code,)).fetchone()
            if row and datetime.fromisoformat(row[1]) > now and row[2] != owner_id:
                return {"status": "blocked", "reason": "lease_held", "lease_id": row[0]}
            lease_id = row[0] if row else "LEASE-" + uuid.uuid4().hex[:12].upper()
            expiry = datetime.fromtimestamp(now.timestamp()+self.lease_seconds, tz=timezone.utc).isoformat()
            c.execute("INSERT OR REPLACE INTO worker_leases VALUES (?,?,?,?,?,?,?)",
                      (lease_id, worker_code, owner_id, "active", now.isoformat(), expiry, now.isoformat()))
            c.commit()
            return {"status": "acquired", "lease_id": lease_id, "expires_at": expiry}

    def heartbeat(self, lease_id, owner_id):
        now = datetime.now(timezone.utc)
        expiry = datetime.fromtimestamp(now.timestamp()+self.lease_seconds, tz=timezone.utc).isoformat()
        with self._db() as c:
            cur = c.execute("UPDATE worker_leases SET expires_at=?,last_heartbeat=? WHERE lease_id=? AND owner_id=? AND status='active'",
                            (expiry, now.isoformat(), lease_id, owner_id))
            c.commit()
            return {"status": "renewed" if cur.rowcount else "blocked", "lease_id": lease_id, "expires_at": expiry}

    def reconcile(self):
        now = datetime.now(timezone.utc)
        with self._db() as c:
            cur = c.execute("UPDATE worker_leases SET status='expired' WHERE status='active' AND expires_at<=?", (now.isoformat(),))
            c.commit()
            active = c.execute("SELECT COUNT(*) FROM worker_leases WHERE status='active'").fetchone()[0]
        return {"status": "ok", "expired": cur.rowcount, "active": active}

    def health(self):
        with self._db() as c:
            active = c.execute("SELECT COUNT(*) FROM worker_leases WHERE status='active'").fetchone()[0]
        return {"status": "ok", "active_leases": active, "lease_seconds": self.lease_seconds}
