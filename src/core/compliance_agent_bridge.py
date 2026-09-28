import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus

class ComplianceAgentBridge:
    """Convert compliance findings into approval-gated remediation proposals."""
    def __init__(self, intelligence, risk_engine, approvals):
        self.intelligence = intelligence
        self.risk_engine = risk_engine
        self.approvals = approvals
        self.events = EventBus()
        self.db_path = os.path.join("data", "compliance_agent_bridge.sqlite3")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS proposals(proposal_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,action_id TEXT,gap_type TEXT,title TEXT,status TEXT,created_at TEXT,approval_id TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_compliance_proposals_scope ON proposals(tenant_id,workspace_id,created_at)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def assess(self, tenant_id, workspace_id, requested_by="system"):
        gaps = self.intelligence.gaps(tenant_id, workspace_id)
        proposals = []
        for gap in gaps:
            if gap["type"] != "unremediated_risk":
                continue
            matrix = self.risk_engine.matrix(tenant_id, workspace_id)
            actions = [x for x in matrix["actions"] if x.get("risk_id") == gap["reference_id"] and x.get("status") not in ("completed", "closed", "cancelled")]
            if actions:
                action = actions[0]
            else:
                action = self.risk_engine.add_action(tenant_id, workspace_id, "Remediate: " + gap["title"], risk_id=gap["reference_id"])
            proposal_id = "CAP-" + uuid.uuid4().hex[:12].upper()
            now = datetime.now(timezone.utc).isoformat()
            with self._db() as c:
                c.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?)", (proposal_id, str(tenant_id), str(workspace_id), action["action_id"], gap["type"], action["title"], "proposed", now, None))
            approval = self.approvals.request(tenant_id, workspace_id, proposal_id, 0, proposal_id, requested_by=requested_by, reason="Compliance remediation requires explicit human approval")
            with self._db() as c:
                c.execute("UPDATE proposals SET approval_id=? WHERE proposal_id=?", (approval["approval_id"], proposal_id))
            self.events.publish("compliance.agent.proposal_created", tenant_id, workspace_id, requested_by, "compliance_proposal", proposal_id, action["action_id"], {"gap_type": gap["type"], "approval_id": approval["approval_id"]}, idempotency_key=proposal_id)
            proposals.append({"proposal_id": proposal_id, "action": action, "gap": gap, "approval": approval})
        return {"status": "ok", "proposals": proposals, "requires_human_approval": True}

    def execute(self, tenant_id, workspace_id, proposal_id, actor_id="system"):
        with self._db() as c:
            row = c.execute("SELECT * FROM proposals WHERE proposal_id=? AND tenant_id=? AND workspace_id=?", (proposal_id, str(tenant_id), str(workspace_id))).fetchone()
        if not row:
            raise ValueError("proposal_not_found")
        approval = self.approvals.for_action(tenant_id, workspace_id, proposal_id, 0)
        if not approval or approval["status"] != "approved":
            self.events.publish("compliance.remediation.approval_blocked", tenant_id, workspace_id, actor_id, "compliance_proposal", proposal_id, row["action_id"], {"reason": "human_approval_required"})
            return {"status": "blocked", "reason": "human_approval_required", "proposal_id": proposal_id, "approval": approval}
        action = self.risk_engine.update_action_status(tenant_id, workspace_id, row["action_id"], "in_progress", actor_id)
        with self._db() as c:
            c.execute("UPDATE proposals SET status='in_progress' WHERE proposal_id=?", (proposal_id,))
        self.events.publish("compliance.remediation.executed", tenant_id, workspace_id, actor_id, "compliance_proposal", proposal_id, row["action_id"], {"status": "in_progress", "approval_id": approval["approval_id"]})
        return {"status": "executed", "proposal_id": proposal_id, "action": action, "approval": approval}

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
        return {"status":"ok","engine":"compliance-agent-bridge","approval_gated":True,"tenant_workspace_scoped":True,"proposals":count}
