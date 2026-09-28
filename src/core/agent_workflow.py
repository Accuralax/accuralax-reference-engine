import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus

ACTIONS = ("assign_owner", "create_followup", "request_consent", "create_opportunity", "advance_stage", "review")

class AgentWorkflow:
    """Rule-driven next-action engine. Decisions are explainable and every action is auditable."""

    def __init__(self, db_path=None, sales_automation=None, pipeline=None, followup_tasks=None, opportunities=None, customer_360=None):
        self.db_path = db_path or os.path.join("data", "agent_workflow.sqlite3")
        self.sales_automation = sales_automation
        self.pipeline = pipeline
        self.followup_tasks = followup_tasks
        self.opportunities = opportunities
        self.customer_360 = customer_360
        self.events = EventBus(os.path.join(os.path.dirname(self.db_path) or ".", "event_bus.sqlite3"))
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decisions(
                decision_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, lead_id TEXT, opportunity_id TEXT, action TEXT NOT NULL,
                reason TEXT NOT NULL, priority TEXT NOT NULL, allowed INTEGER NOT NULL,
                executed INTEGER NOT NULL, created_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_decision_scope ON decisions(tenant_id,workspace_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS processed_events(event_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _on_event(self, event):
        """Turn a domain event into an auditable decision; never execute side effects here."""
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            existing = c.execute("SELECT 1 FROM processed_events WHERE event_id=?", (event.event_id,)).fetchone()
            if existing:
                row = c.execute("SELECT decision_id FROM decisions WHERE reason LIKE ? ORDER BY created_at DESC LIMIT 1",
                                (f"%{event.event_id}%",)).fetchone()
                return row[0] if row else None
            action = "request_consent" if event.event_type == "sales.lead.created" else "review"
            priority = "high" if action == "request_consent" else "normal"
            reason = f"Domain event {event.event_type} ({event.event_id}) requires governed review"
            did = "DEC-" + uuid.uuid4().hex[:16].upper()
            payload = event.payload or {}
            client_id = str(payload.get("client_id") or event.entity_id)
            lead_id = str(payload.get("lead_id") or event.entity_id) if event.entity_type == "lead" else None
            opportunity_id = str(payload.get("opportunity_id") or event.entity_id) if event.entity_type == "opportunity" else None
            c.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (did, event.tenant_id, event.workspace_id, client_id, lead_id, opportunity_id,
                       action, reason, priority, 1, 0, now))
            c.execute("INSERT INTO processed_events(event_id,processed_at) VALUES(?,?)", (event.event_id, now))
        return did

    def consume_event(self, event):
        return self._on_event(event)

    def process_pending_events(self, tenant_id, workspace_id, limit=100):
        """Process durable events so delivery works across separate EventBus instances."""
        allowed = {"sales.lead.created", "sales.lead.stage_changed", "sales.opportunity.created",
                   "sales.opportunity.stage_changed", "lms.progress.recorded", "lms.attendance.recorded",
                   "lms.assessment.status_changed"}
        events = self.events.history(str(tenant_id), str(workspace_id), limit=limit)
        processed = []
        for event in reversed(events):
            if event.event_type in allowed:
                decision_id = self._on_event(event)
                if decision_id:
                    processed.append(decision_id)
        return {"processed": len(processed), "decision_ids": processed}

    def decide(self, tenant_id, workspace_id, client_id, lead=None, opportunity=None,
               consent_granted=False, open_tasks=0):
        actions = []
        stage = (lead or {}).get("status", "new")
        score = float((lead or {}).get("score") or 0)
        value = float((opportunity or {}).get("value") or 0)
        opp_status = (opportunity or {}).get("status", "none")

        if lead and not lead.get("owner_id"):
            actions.append(("assign_owner", "Lead has no owner", "high", True))
        if not consent_granted:
            actions.append(("request_consent", "Outbound sales communication requires consent", "high", True))
        elif open_tasks == 0 and lead:
            actions.append(("create_followup", "No open follow-up task exists", "high" if score >= 70 else "normal", True))
        if lead and score >= 70 and not opportunity:
            actions.append(("create_opportunity", "Lead score meets opportunity threshold", "normal", True))
        if opportunity and opp_status == "open" and stage in ("proposal", "negotiation"):
            actions.append(("advance_stage", "Opportunity and lead are in an active commercial stage", "normal", True))
        if not actions:
            actions.append(("review", "No deterministic automated action is currently required", "low", True))

        now = datetime.now(timezone.utc).isoformat()
        result = []
        with self._db() as c:
            for action, reason, priority, allowed in actions:
                did = "DEC-" + uuid.uuid4().hex[:16].upper()
                c.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                          (did, str(tenant_id), str(workspace_id), str(client_id),
                           (lead or {}).get("lead_id"), (opportunity or {}).get("opportunity_id"),
                           action, reason, priority, int(allowed), 0, now))
                result.append({"decision_id": did, "action": action, "reason": reason,
                               "priority": priority, "allowed": allowed, "executed": False})
        return {"client_id": str(client_id), "context": {"lead_stage": stage, "lead_score": score,
                "opportunity_value": value, "opportunity_status": opp_status,
                "consent_granted": bool(consent_granted), "open_tasks": int(open_tasks)},
                "next_actions": result}

    def execute(self, tenant_id, workspace_id, decision_id, owner_id=None, task=None, opportunity=None, changed_by="agent"):
        with self._db() as c:
            row = c.execute("SELECT * FROM decisions WHERE tenant_id=? AND workspace_id=? AND decision_id=?",
                            (str(tenant_id), str(workspace_id), str(decision_id))).fetchone()
        if not row:
            raise ValueError("decision_not_found")
        if row["executed"]:
            return {"status": "already_executed", "decision": dict(row)}
        action = row["action"]
        result = {"decision_id": decision_id, "action": action, "status": "blocked"}
        if action == "request_consent":
            result["reason"] = "consent must be explicitly granted before outbound action"
            return result
        if action == "assign_owner":
            if not self.pipeline or not owner_id:
                result["reason"] = "pipeline_engine_and_owner_id_required"
                return result
            result["result"] = self.pipeline.assign_owner(tenant_id, workspace_id, row["lead_id"], owner_id)
        elif action == "create_followup":
            if not self.followup_tasks:
                result["reason"] = "followup_task_engine_required"
                return result
            task = task or {}
            result["result"] = self.followup_tasks.create(
                tenant_id, workspace_id, row["client_id"], task.get("title", "Sales follow-up"),
                task.get("due_at"), owner_id or task.get("owner_id"), row["lead_id"],
                row["opportunity_id"], task.get("channel", "internal"),
                task.get("priority", row["priority"]), task.get("notes", row["reason"]))
        elif action == "create_opportunity":
            if not self.opportunities:
                result["reason"] = "opportunity_engine_required"
                return result
            opportunity = opportunity or {}
            if not opportunity.get("name"):
                result["reason"] = "opportunity_name_required"
                return result
            result["result"] = self.opportunities.create(
                tenant_id, workspace_id, row["client_id"], opportunity["name"],
                opportunity.get("value"), opportunity.get("currency"),
                opportunity.get("probability", 0), opportunity.get("expected_close_date"),
                row["lead_id"])
        elif action == "advance_stage":
            if not self.opportunities or not row["opportunity_id"]:
                result["reason"] = "opportunity_engine_required"
                return result
            result["result"] = self.opportunities.update_stage(
                tenant_id, workspace_id, row["opportunity_id"],
                (opportunity or {}).get("stage", "proposal"), changed_by, row["reason"])
        else:
            result["reason"] = "action_requires_review_or_is_not_executable"
            return result

        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE decisions SET executed=1 WHERE tenant_id=? AND workspace_id=? AND decision_id=?",
                      (str(tenant_id), str(workspace_id), str(decision_id)))
        if self.customer_360:
            self.customer_360.record_event(
                tenant_id, workspace_id, row["client_id"], "agent", "workflow_action_executed",
                action, occurred_at=now, metadata={"decision_id": decision_id})
        result["status"] = "executed"
        return result

    def mark_executed(self, tenant_id, workspace_id, decision_id):
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            row = c.execute("SELECT * FROM decisions WHERE tenant_id=? AND workspace_id=? AND decision_id=?",
                            (str(tenant_id), str(workspace_id), str(decision_id))).fetchone()
            if not row:
                raise ValueError("decision_not_found")
            c.execute("UPDATE decisions SET executed=1 WHERE tenant_id=? AND workspace_id=? AND decision_id=?",
                      (str(tenant_id), str(workspace_id), str(decision_id)))
        return {**dict(row), "executed": True, "executed_at": now}

    def history(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            rows = c.execute("SELECT * FROM decisions WHERE tenant_id=? AND workspace_id=? AND client_id=? ORDER BY created_at",
                             (str(tenant_id), str(workspace_id), str(client_id))).fetchall()
        return [dict(r) for r in rows]

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        return {"status":"ok","engine":"agent-workflow","rule_driven":True,
                "explainable_decisions":True,"action_audit":True,"tenant_workspace_scoped":True,
                "credentials_exposed":False,"decisions":count}
