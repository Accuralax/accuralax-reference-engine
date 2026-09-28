import os
import sqlite3
import uuid
from datetime import datetime, timezone

class SalesAutomation:
    """Deterministic, consent-aware orchestration for lead-to-opportunity sales actions."""

    def __init__(self, db_path=None, pipeline=None, opportunities=None, customer_360=None):
        self.db_path = db_path or os.path.join("data", "sales_automation.sqlite3")
        self.pipeline = pipeline
        self.opportunities = opportunities
        self.customer_360 = customer_360
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS automation_runs(
                run_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, lead_id TEXT, opportunity_id TEXT, action TEXT NOT NULL,
                status TEXT NOT NULL, consent_required INTEGER NOT NULL, consent_granted INTEGER NOT NULL,
                details TEXT, created_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_automation_scope ON automation_runs(tenant_id,workspace_id,created_at)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _audit(self, tenant_id, workspace_id, client_id, action, status, consent_required, consent_granted,
               lead_id=None, opportunity_id=None, details=""):
        now = datetime.now(timezone.utc).isoformat()
        run_id = "AUT-" + uuid.uuid4().hex[:16].upper()
        with self._db() as c:
            c.execute("INSERT INTO automation_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (run_id, str(tenant_id), str(workspace_id), str(client_id), lead_id, opportunity_id,
                       action, status, int(consent_required), int(consent_granted), str(details), now))
        return run_id

    def intake(self, tenant_id, workspace_id, client_id, source="unknown", score=0, owner_id=None,
               name="New enquiry", notes="", consent_granted=False):
        if not str(client_id).strip():
            raise ValueError("client_id_required")
        score = max(0, min(100, int(score)))
        if not self.pipeline:
            raise ValueError("pipeline_engine_required")
        lead = self.pipeline.create_lead(tenant_id, workspace_id, client_id, source, owner_id, score, notes)
        if owner_id:
            self.pipeline.assign_owner(tenant_id, workspace_id, lead["lead_id"], owner_id)
            lead = self.pipeline.get_lead(tenant_id, workspace_id, lead["lead_id"])
        self._audit(tenant_id, workspace_id, client_id, "lead_intake", "completed", False, consent_granted,
                    lead_id=lead["lead_id"], details="lead_created")
        if self.customer_360:
            self.customer_360.record_event(tenant_id, workspace_id, client_id, source, "sales_lead_intake",
                                           "Sales lead received", metadata={"lead_id": lead["lead_id"], "score": score})
        return {"lead": lead, "outreach_allowed": bool(consent_granted), "consent_required_for_outreach": True}

    def authorize_outreach(self, tenant_id, workspace_id, client_id, consent_granted, purpose="sales_outreach"):
        if not self.customer_360:
            raise ValueError("customer_360_required")
        consent = self.customer_360.set_consent(tenant_id, workspace_id, client_id, purpose, bool(consent_granted), "sales_automation")
        self._audit(tenant_id, workspace_id, client_id, "consent", "completed", True, bool(consent_granted),
                    details=purpose)
        return consent

    def outreach_gate(self, tenant_id, workspace_id, client_id, purpose="sales_outreach"):
        if not self.customer_360:
            return {"allowed": False, "reason": "customer_360_required"}
        allowed = bool(self.customer_360.handoff_allowed(tenant_id, workspace_id, client_id, purpose))
        return {"allowed": allowed, "reason": "consent_granted" if allowed else "consent_required"}

    def create_opportunity(self, tenant_id, workspace_id, client_id, name, value, currency,
                           probability=0, expected_close_date=None, lead_id=None):
        if not self.opportunities:
            raise ValueError("opportunity_engine_required")
        opp = self.opportunities.create(tenant_id, workspace_id, client_id, name, value, currency,
                                        probability, expected_close_date, lead_id)
        self._audit(tenant_id, workspace_id, client_id, "opportunity_creation", "completed", False, False,
                    lead_id=lead_id, opportunity_id=opp["opportunity_id"], details="opportunity_created")
        if self.customer_360:
            self.customer_360.record_event(tenant_id, workspace_id, client_id, "sales", "opportunity_created",
                                           "Sales opportunity created", metadata={"opportunity_id": opp["opportunity_id"]})
        return opp

    def history(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            rows = c.execute("SELECT * FROM automation_runs WHERE tenant_id=? AND workspace_id=? AND client_id=? ORDER BY created_at",
                             (str(tenant_id), str(workspace_id), str(client_id))).fetchall()
        return [dict(r) for r in rows]

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM automation_runs").fetchone()[0]
        return {"status":"ok","engine":"sales-automation","tenant_workspace_scoped":True,
                "consent_gate":True,"action_audit":True,"credentials_exposed":False,"runs":count}
