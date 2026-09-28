"""Enterprise compliance orchestration layer."""
from __future__ import annotations
import json, os, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class ComplianceOrchestrator:
    """Coordinates assessment, explicit approval, governed execution and lineage."""
    def __init__(self, report_agent, bridge, events, db_path=None, planner=None, executor=None, outcome_analytics=None, regulatory_intelligence=None, compliance_risk=None):
        self.report_agent = report_agent
        self.bridge = bridge
        self.events = events
        self.planner = planner
        self.executor = executor
        self.outcome_analytics = outcome_analytics
        self.regulatory_intelligence = regulatory_intelligence
        self.compliance_risk = compliance_risk or getattr(bridge, "risk_engine", None)
        self.db_path = db_path or os.path.join("data", "compliance_orchestrator.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS compliance_runs (run_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL, report_id TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS compliance_run_proposals (run_id TEXT NOT NULL, proposal_id TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(run_id, proposal_id))")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path); c.row_factory = sqlite3.Row
        try:
            yield c; c.commit()
        finally: c.close()

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def _emit(self, event_type, tenant_id, workspace_id, entity_id, payload):
        return self.events.publish(event_type, tenant_id, workspace_id, "compliance-orchestrator", "compliance_run", entity_id, entity_id, payload, idempotency_key=entity_id + ":" + event_type)

    def process_event(self, event):
        """Idempotently turn a compliance assessment event into an orchestrated run."""
        if event.event_type != "compliance.assessment.requested":
            return {"status": "ignored", "reason": "event_not_supported"}
        tenant_id, workspace_id = str(event.tenant_id), str(event.workspace_id)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS compliance_event_once (tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL, event_id TEXT NOT NULL, run_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(tenant_id,workspace_id,event_id))")
            row = c.execute("SELECT run_id FROM compliance_event_once WHERE tenant_id=? AND workspace_id=? AND event_id=?", (tenant_id, workspace_id, str(event.event_id))).fetchone()
        if row:
            existing = self.get(tenant_id, workspace_id, row["run_id"])
            return {"status": "already_processed", "run_id": row["run_id"], "result": existing}
        payload = event.payload or {}
        result = self.assess(
            tenant_id, workspace_id,
            requested_by=str(payload.get("requested_by") or event.actor_id or "system"),
            regulation_id=payload.get("regulation_id"),
            organization_profile=payload.get("organization_profile") or {},
        )
        with self._db() as c:
            c.execute("INSERT OR IGNORE INTO compliance_event_once VALUES(?,?,?,?,?)", (tenant_id, workspace_id, str(event.event_id), result["run_id"], self._now()))
        return result

    def _sync_regulatory_impact(self, tenant_id, workspace_id, impact):
        if not self.compliance_risk or not impact or not impact.get("applicable"):
            return {"obligations":[],"risks":[]}
        synced=[]; risks=[]
        for item in impact.get("obligations",[]):
            source=f"regulatory:{impact['assessment']['regulation_id']}:obligation:{item['obligation_id']}"
            existing=self.compliance_risk.find_obligation_by_source(tenant_id,workspace_id,source)
            obligation=existing or self.compliance_risk.add_obligation(
                tenant_id,workspace_id,item["title"],source=source,due_at=item.get("deadline") or None
            )
            synced.append(obligation)
            if item.get("priority") in ("high","critical"):
                existing_risks=[r for r in self.compliance_risk.matrix(tenant_id,workspace_id)["risks"] if r.get("obligation_id")==obligation["obligation_id"] and r.get("status") not in ("closed","mitigated")]
                if existing_risks:
                    risks.append(existing_risks[0])
                else:
                    risks.append(self.compliance_risk.assess_risk(
                        tenant_id,workspace_id,"Regulatory impact: "+item["title"],
                    4 if item["priority"]=="critical" else 3,
                    5 if item["priority"]=="critical" else 4,
                    obligation_id=obligation["obligation_id"],
                    treatment="Regulatory change review and remediation"
                ))
        return {"obligations":synced,"risks":risks}

    def assess(self, tenant_id, workspace_id, requested_by="system", regulation_id=None, organization_profile=None):
        regulatory_impact = None
        if regulation_id and self.regulatory_intelligence:
            regulatory_impact = self.regulatory_intelligence.impact_assessment(
                tenant_id, workspace_id, regulation_id, organization_profile or {}
            )
            if not regulatory_impact.get("applicable"):
                return {"run_id":"COR-"+uuid.uuid4().hex[:12].upper(),"status":"not_applicable","report":None,"proposals":[],"regulatory_impact":regulatory_impact}
        if regulatory_impact:
            regulatory_impact["risk_sync"] = self._sync_regulatory_impact(tenant_id, workspace_id, regulatory_impact)
        report = self.report_agent.generate(tenant_id, workspace_id, generated_by=requested_by)
        bridge_result = self.bridge.assess(tenant_id, workspace_id, requested_by=requested_by)
        proposals = bridge_result.get("proposals", [])
        run_id = "COR-" + uuid.uuid4().hex[:12].upper(); now = self._now()
        status = "awaiting_approval" if proposals else "completed"
        with self._db() as c:
            c.execute("INSERT INTO compliance_runs VALUES (?,?,?,?,?,?,?)", (run_id,str(tenant_id),str(workspace_id),report["report_id"],status,now,now))
            for p in proposals:
                c.execute("INSERT OR IGNORE INTO compliance_run_proposals VALUES (?,?,?)", (run_id,p["proposal_id"],"pending"))
        self._emit("compliance.orchestration.assessed",tenant_id,workspace_id,run_id,{"report_id":report["report_id"],"proposal_count":len(proposals)})
        return {"run_id":run_id,"status":status,"report":report,"proposals":proposals,"regulatory_impact":regulatory_impact}

    def get(self, tenant_id, workspace_id, run_id):
        with self._db() as c:
            row=c.execute("SELECT * FROM compliance_runs WHERE run_id=? AND tenant_id=? AND workspace_id=?",(run_id,str(tenant_id),str(workspace_id))).fetchone()
            if not row: return None
            props=[dict(x) for x in c.execute("SELECT * FROM compliance_run_proposals WHERE run_id=?",(run_id,))]
        return {"run":dict(row),"proposals":props}

    def approve_proposal(self, tenant_id, workspace_id, run_id, proposal_id, approved, actor_id, reason=""):
        if not self.get(tenant_id,workspace_id,run_id): raise ValueError("run_not_found")
        with self.bridge._db() as c:
            row=c.execute("SELECT approval_id FROM proposals WHERE proposal_id=? AND tenant_id=? AND workspace_id=?",(proposal_id,str(tenant_id),str(workspace_id))).fetchone()
        if not row: raise ValueError("proposal_not_found")
        approval = self.bridge.approvals.decide(tenant_id,workspace_id,row["approval_id"],bool(approved),actor_id,reason)
        status = approval["status"]
        with self._db() as c:
            c.execute("UPDATE compliance_run_proposals SET status=? WHERE run_id=? AND proposal_id=?",(status,run_id,proposal_id))
            c.execute("UPDATE compliance_runs SET updated_at=? WHERE run_id=?",(self._now(),run_id))
        self._emit("compliance.orchestration.approval",tenant_id,workspace_id,run_id,{"proposal_id":proposal_id,"approval_id":approval["approval_id"],"status":status,"actor_id":str(actor_id)})
        return {"run_id":run_id,"proposal_id":proposal_id,"status":status,"approval":approval}

    def execute(self, tenant_id, workspace_id, run_id, actor_id="system"):
        item=self.get(tenant_id,workspace_id,run_id)
        if not item: raise ValueError("run_not_found")
        if any(p["status"] != "approved" for p in item["proposals"]):
            return {"run_id":run_id,"status":"blocked_pending_approval","executed":[]}
        results=[]
        for p in item["proposals"]:
            results.append(self.bridge.execute(tenant_id,workspace_id,p["proposal_id"],actor_id=actor_id))
            with self._db() as c: c.execute("UPDATE compliance_run_proposals SET status=? WHERE run_id=? AND proposal_id=?",("executed" if results[-1].get("status")=="executed" else p["status"],run_id,p["proposal_id"]))
        final="completed" if all(r.get("status")=="executed" for r in results) else "execution_blocked"
        with self._db() as c: c.execute("UPDATE compliance_runs SET status=?,updated_at=? WHERE run_id=?",(final,self._now(),run_id))
        payload={"actor_id":str(actor_id),"results":results}
        self._emit("compliance.orchestration.executed",tenant_id,workspace_id,run_id,payload)
        if self.outcome_analytics:
            try:
                payload["outcome_analytics"] = self.outcome_analytics.analyze(tenant_id, workspace_id)
            except Exception as exc:
                payload["outcome_analytics_error"] = str(exc)
        return {"run_id":run_id,"status":final,"executed":results,"outcome_analytics":payload.get("outcome_analytics", [])}

    def process_regulatory_change(self, tenant_id, workspace_id, regulation_id, new_version, organization_profile=None, requested_by="system", impact="medium", checksum="", proposed_obligations=None):
        """Detect a regulatory change, publish a durable change event, then route assessment through the governed event path."""
        if not self.regulatory_intelligence:
            return {"status":"blocked","reason":"regulatory_intelligence_unavailable"}
        change = self.regulatory_intelligence.detect_change(
            tenant_id, workspace_id, regulation_id, new_version,
            impact=impact, checksum=checksum
        )
        if not change.get("changed"):
            return change
        obligation_diff = self.regulatory_intelligence.compare_obligations(
            tenant_id, workspace_id, regulation_id, proposed_obligations
        ) if proposed_obligations is not None else {"added":[],"removed":[],"changed":[],"total_affected":0}
        obligation_sync = self.regulatory_intelligence.apply_obligation_diff(
            tenant_id, workspace_id, regulation_id, new_version, obligation_diff
        ) if proposed_obligations is not None else {"created":[],"superseded":[]}
        asset_diff = self.regulatory_intelligence.compare_controls_and_evidence(
            tenant_id, workspace_id, regulation_id, proposed_obligations
        ) if proposed_obligations is not None else {"added_controls":[],"removed_controls":[],"added_evidence":[],"removed_evidence":[]}
        asset_sync = self.regulatory_intelligence.apply_control_evidence_diff(
            tenant_id, workspace_id, regulation_id, asset_diff
        ) if proposed_obligations is not None else {"controls_linked":[],"controls_retired":[],"evidence_added":[],"evidence_retired":[]}
        payload={
            "regulation_id": regulation_id, "old_version": change["old_version"],
            "new_version": change["new_version"], "impact": change["impact"],
            "change_id": change["change"]["change_id"], "requested_by": requested_by,
            "obligation_diff": obligation_diff, "obligation_sync": obligation_sync,
            "asset_diff": asset_diff, "asset_sync": asset_sync,
        }
        event=self.events.publish(
            "compliance.regulatory.change.detected", str(tenant_id), str(workspace_id),
            str(requested_by or "system"), "regulation", str(regulation_id),
            str(change["change"]["change_id"]), payload,
            idempotency_key=f"regulatory-change:{tenant_id}:{workspace_id}:{regulation_id}:{new_version}"
        )
        assessment_event=self.events.publish(
            "compliance.assessment.requested", str(tenant_id), str(workspace_id),
            str(requested_by or "system"), "regulation", str(regulation_id),
            str(change["change"]["change_id"])+":assessment",
            {"regulation_id":regulation_id,"organization_profile":organization_profile or {},"requested_by":requested_by,"change_id":change["change"]["change_id"],"impact":impact},
            idempotency_key=f"regulatory-assessment:{tenant_id}:{workspace_id}:{regulation_id}:{new_version}"
        )
        result=self.process_event(assessment_event)
        return {"status":"processed","change":change,"change_event":event,"assessment_event":assessment_event,"assessment":result,"obligation_diff":obligation_diff,"obligation_sync":obligation_sync,"asset_diff":asset_diff}

    def intelligence_snapshot(self, tenant_id, workspace_id):
        """Return the current compliance intelligence plus orchestration outcome signals."""
        result={"compliance": self.report_agent.intelligence.summary(tenant_id, workspace_id)}
        result["gaps"]=self.report_agent.intelligence.gaps(tenant_id, workspace_id)
        result["recommendations"]=self.report_agent.intelligence.recommendations(tenant_id, workspace_id)
        if self.outcome_analytics:
            result["agent_outcomes"]=self.outcome_analytics.analyze(tenant_id, workspace_id)
        return result
