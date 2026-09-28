import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus

DB_PATH = os.getenv("SALES_PIPELINE_DB_PATH", os.path.join("data", "sales_pipeline.sqlite3"))
STAGES = ("new_enquiry", "qualified", "discovery", "proposal", "negotiation", "won", "lost")

class SalesPipeline:
    """Tenant-scoped lead pipeline anchored to canonical CRM client IDs."""

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        event_path = os.path.join(os.path.dirname(db_path) or ".", "event_bus.sqlite3")
        self.events = EventBus(event_path)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS leads(
                lead_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, source TEXT NOT NULL, owner_id TEXT, status TEXT NOT NULL,
                score INTEGER, notes TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS lead_stage_history(
                history_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                lead_id TEXT NOT NULL, from_stage TEXT, to_stage TEXT NOT NULL,
                changed_by TEXT NOT NULL, changed_at TEXT NOT NULL, reason TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_leads_scope_status ON leads(tenant_id,workspace_id,status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_lead_history ON lead_stage_history(tenant_id,workspace_id,lead_id,changed_at)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    @staticmethod
    def _scope(tenant_id, workspace_id):
        return str(tenant_id), str(workspace_id)

    @staticmethod
    def _client(client_id):
        if not str(client_id).strip():
            raise ValueError("client_id_required")

    @staticmethod
    def _stage(stage):
        stage = str(stage)
        if stage not in STAGES:
            raise ValueError("invalid_stage")
        return stage

    def create_lead(self, tenant_id, workspace_id, client_id, source="unknown", owner_id=None, score=None, notes=""):
        # Backward-compatible shorthand: a numeric fifth positional argument is a lead score.
        if score is None and isinstance(owner_id, (int, float)):
            score, owner_id = owner_id, None
        self._client(client_id)
        now = datetime.now(timezone.utc).isoformat()
        lead_id = "LED-" + uuid.uuid4().hex[:16].upper()
        item = (lead_id, *self._scope(tenant_id, workspace_id), str(client_id), str(source),
                str(owner_id) if owner_id else None, "new_enquiry", score, str(notes), now, now)
        with self._db() as c:
            c.execute("INSERT INTO leads VALUES(?,?,?,?,?,?,?,?,?,?,?)", item)
            c.execute("INSERT INTO lead_stage_history VALUES(?,?,?,?,?,?,?,?,?)",
                      ("HST-" + uuid.uuid4().hex[:16].upper(), str(tenant_id), str(workspace_id),
                       lead_id, None, "new_enquiry", "system", now, "lead_created"))
        result = self.get_lead(tenant_id, workspace_id, lead_id)
        self.events.publish("sales.lead.created", tenant_id, workspace_id, "system", "lead", lead_id, lead_id, {"client_id": client_id, "source": source, "status": "new_enquiry"}, idempotency_key=f"lead-created:{lead_id}")
        return result

    def get_lead(self, tenant_id, workspace_id, lead_id):
        with self._db() as c:
            row = c.execute("SELECT * FROM leads WHERE tenant_id=? AND workspace_id=? AND lead_id=?",
                            (*self._scope(tenant_id, workspace_id), str(lead_id))).fetchone()
        return dict(row) if row else None

    def move_stage(self, tenant_id, workspace_id, lead_id, to_stage, changed_by="system", reason=""):
        to_stage = self._stage(to_stage)
        lead = self.get_lead(tenant_id, workspace_id, lead_id)
        if not lead:
            raise ValueError("lead_not_found")
        if lead["status"] == to_stage:
            return lead
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE leads SET status=?, updated_at=? WHERE tenant_id=? AND workspace_id=? AND lead_id=?",
                      (to_stage, now, *self._scope(tenant_id, workspace_id), str(lead_id)))
            c.execute("INSERT INTO lead_stage_history VALUES(?,?,?,?,?,?,?,?,?)",
                      ("HST-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id, workspace_id),
                       str(lead_id), lead["status"], to_stage, str(changed_by), now, str(reason)))
        result = self.get_lead(tenant_id, workspace_id, lead_id)
        self.events.publish("sales.lead.stage_changed", tenant_id, workspace_id, str(changed_by), "lead", lead_id, lead_id, {"from_stage": lead["status"], "to_stage": to_stage, "reason": reason})
        return result

    def assign_owner(self, tenant_id, workspace_id, lead_id, owner_id):
        if not str(owner_id).strip():
            raise ValueError("owner_id_required")
        lead = self.get_lead(tenant_id, workspace_id, lead_id)
        if not lead:
            raise ValueError("lead_not_found")
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE leads SET owner_id=?, updated_at=? WHERE tenant_id=? AND workspace_id=? AND lead_id=?",
                      (str(owner_id), now, *self._scope(tenant_id, workspace_id), str(lead_id)))
        return self.get_lead(tenant_id, workspace_id, lead_id)

    def history(self, tenant_id, workspace_id, lead_id):
        with self._db() as c:
            rows = c.execute("""SELECT * FROM lead_stage_history
                WHERE tenant_id=? AND workspace_id=? AND lead_id=? ORDER BY changed_at""",
                (*self._scope(tenant_id, workspace_id), str(lead_id))).fetchall()
        return [dict(r) for r in rows]

    def pipeline(self, tenant_id, workspace_id):
        with self._db() as c:
            rows = c.execute("""SELECT status, COUNT(*) AS count,
                COALESCE(SUM(value),0) AS value FROM leads
                LEFT JOIN (SELECT NULL AS value) ON 1=0
                WHERE tenant_id=? AND workspace_id=? GROUP BY status""",
                self._scope(tenant_id, workspace_id)).fetchall()
        counts = {stage: {"count": 0} for stage in STAGES}
        for row in rows:
            counts[row["status"]] = {"count": row["count"]}
        return {"stages": counts, "total_leads": sum(v["count"] for v in counts.values())}

    def health(self):
        with self._db() as c:
            leads = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            history = c.execute("SELECT COUNT(*) FROM lead_stage_history").fetchone()[0]
        return {"status": "ok", "engine": "sales-pipeline", "tenant_workspace_scoped": True,
                "canonical_client_anchor": True, "stage_audit": True,
                "credentials_exposed": False, "leads": leads, "stage_history": history}
