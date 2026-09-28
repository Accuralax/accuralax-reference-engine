import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class HumanApprovalGateway:
    """Tenant-scoped, explicit approval records for consequential agent actions."""
    STATUSES = ("requested", "approved", "rejected", "expired", "revoked")

    def __init__(self, db_path=None, default_ttl_minutes=30):
        self.db_path = db_path or os.path.join("data", "human_approvals.sqlite3")
        self.default_ttl_minutes = max(1, int(default_ttl_minutes))
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS approvals(
                approval_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, plan_id TEXT NOT NULL,
                position INTEGER NOT NULL, decision_id TEXT NOT NULL,
                status TEXT NOT NULL, requested_by TEXT NOT NULL,
                requested_at TEXT NOT NULL, approved_by TEXT,
                approved_at TEXT, reason TEXT NOT NULL, expires_at TEXT NOT NULL,
                UNIQUE(tenant_id,workspace_id,plan_id,position))""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_approval_scope ON approvals(tenant_id,workspace_id,status)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _now(self):
        return datetime.now(timezone.utc)

    def request(self, tenant_id, workspace_id, plan_id, position, decision_id,
                requested_by="system", reason="", ttl_minutes=None):
        now = self._now()
        ttl = max(1, int(ttl_minutes or self.default_ttl_minutes))
        expires = now.timestamp() + ttl * 60
        expires_at = datetime.fromtimestamp(expires, timezone.utc).isoformat()
        approval_id = "APR-" + uuid.uuid4().hex[:16].upper()
        with self._db() as c:
            existing = c.execute("""SELECT * FROM approvals
                WHERE tenant_id=? AND workspace_id=? AND plan_id=? AND position=?""",
                (str(tenant_id), str(workspace_id), str(plan_id), int(position))).fetchone()
            if existing and existing["status"] in ("requested", "approved"):
                return dict(existing)
            c.execute("""INSERT OR REPLACE INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (approval_id, str(tenant_id), str(workspace_id), str(plan_id), int(position),
                 str(decision_id), "requested", str(requested_by), now.isoformat(),
                 None, None, str(reason), expires_at))
        return self.get(tenant_id, workspace_id, approval_id)
    def _expire_if_needed(self, row):
        if row["status"] == "requested" and row["expires_at"] <= self._now().isoformat():
            with self._db() as c:
                c.execute("UPDATE approvals SET status='expired' WHERE approval_id=?", (row["approval_id"],))
            return {**dict(row), "status": "expired"}
        return dict(row)

    def get(self, tenant_id, workspace_id, approval_id):
        with self._db() as c:
            row = c.execute("SELECT * FROM approvals WHERE tenant_id=? AND workspace_id=? AND approval_id=?",
                            (str(tenant_id), str(workspace_id), str(approval_id))).fetchone()
        if not row:
            raise ValueError("approval_not_found")
        return self._expire_if_needed(row)

    def for_action(self, tenant_id, workspace_id, plan_id, position):
        with self._db() as c:
            row = c.execute("""SELECT * FROM approvals
                WHERE tenant_id=? AND workspace_id=? AND plan_id=? AND position=?""",
                (str(tenant_id), str(workspace_id), str(plan_id), int(position))).fetchone()
        if not row:
            return None
        return self._expire_if_needed(row)

    def decide(self, tenant_id, workspace_id, approval_id, approved, actor_id, reason=""):
        current = self.get(tenant_id, workspace_id, approval_id)
        if current["status"] != "requested":
            return current
        status = "approved" if bool(approved) else "rejected"
        now = self._now().isoformat()
        with self._db() as c:
            c.execute("""UPDATE approvals SET status=?, approved_by=?, approved_at=?, reason=?
                WHERE tenant_id=? AND workspace_id=? AND approval_id=? AND status='requested'""",
                (status, str(actor_id), now, str(reason or current["reason"]),
                 str(tenant_id), str(workspace_id), str(approval_id)))
        return self.get(tenant_id, workspace_id, approval_id)

    def approve(self, tenant_id, workspace_id, approval_id, actor_id, reason=""):
        return self.decide(tenant_id, workspace_id, approval_id, True, actor_id, reason)

    def reject(self, tenant_id, workspace_id, approval_id, actor_id, reason=""):
        return self.decide(tenant_id, workspace_id, approval_id, False, actor_id, reason)
    def revoke(self, tenant_id, workspace_id, approval_id, actor_id, reason=""):
        current = self.get(tenant_id, workspace_id, approval_id)
        if current["status"] not in ("approved", "requested"):
            return current
        with self._db() as c:
            c.execute("""UPDATE approvals SET status='revoked', approved_by=?, approved_at=?, reason=?
                WHERE tenant_id=? AND workspace_id=? AND approval_id=?""",
                (str(actor_id), self._now().isoformat(), str(reason), str(tenant_id),
                 str(workspace_id), str(approval_id)))
        return self.get(tenant_id, workspace_id, approval_id)

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
        return {"status":"ok", "engine":"human-approval-gateway", "explicit_approval":True,
                "tenant_workspace_scoped":True, "fail_closed":True, "approvals":count}
