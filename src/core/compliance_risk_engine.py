import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class ComplianceRiskEngine:
    STATUSES = ("open","in_progress","compliant","non_compliant","accepted","closed")
    RISK_LEVELS = ("low","medium","high","critical")

    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","compliance_risk.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS obligations(obligation_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,jurisdiction TEXT,authority TEXT,source TEXT,due_at TEXT,status TEXT,owner_id TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS controls(control_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,obligation_id TEXT,name TEXT,description TEXT,owner_id TEXT,status TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS risks(risk_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,obligation_id TEXT,title TEXT,likelihood INTEGER,impact INTEGER,score INTEGER,level TEXT,status TEXT,treatment TEXT,owner_id TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,obligation_id TEXT,control_id TEXT,title TEXT,reference TEXT,verified INTEGER,verified_by TEXT,verified_at TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS actions(action_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,risk_id TEXT,obligation_id TEXT,title TEXT,owner_id TEXT,due_at TEXT,status TEXT,created_at TEXT,updated_at TEXT)")

    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try:
            yield c; c.commit()
        finally: c.close()

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def _id(prefix): return f"{prefix}-{uuid.uuid4().hex[:12]}"
    @staticmethod
    def _row(row): return dict(row) if row else None

    def find_obligation_by_source(self, tenant_id, workspace_id, source):
        with self._db() as c:
            row=c.execute("SELECT * FROM obligations WHERE tenant_id=? AND workspace_id=? AND source=? ORDER BY created_at DESC LIMIT 1",(str(tenant_id),str(workspace_id),str(source))).fetchone()
        return self._row(row)

    def add_or_get_obligation(self,tenant_id,workspace_id,name,jurisdiction="",authority="",source="",due_at=None,owner_id=None):
        existing=self.find_obligation_by_source(tenant_id,workspace_id,source) if source else None
        if existing: return existing
        return self.add_obligation(tenant_id,workspace_id,name,jurisdiction,authority,source,due_at,owner_id)

    def add_obligation(self,tenant_id,workspace_id,name,jurisdiction="",authority="",source="",due_at=None,owner_id=None):
        now=self._now(); oid=self._id("OBL")
        with self._db() as c: c.execute("INSERT INTO obligations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(oid,str(tenant_id),str(workspace_id),name,jurisdiction,authority,source,due_at,"open",owner_id,now,now))
        return self.get_obligation(tenant_id,workspace_id,oid)

    def get_obligation(self,tenant_id,workspace_id,obligation_id):
        with self._db() as c: return self._row(c.execute("SELECT * FROM obligations WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(obligation_id,str(tenant_id),str(workspace_id))).fetchone())

    def add_control(self,tenant_id,workspace_id,obligation_id,name,description="",owner_id=None):
        if not self.get_obligation(tenant_id,workspace_id,obligation_id): raise ValueError("obligation_not_found")
        cid=self._id("CTL")
        with self._db() as c: c.execute("INSERT INTO controls VALUES(?,?,?,?,?,?,?,?,?)",(cid,str(tenant_id),str(workspace_id),obligation_id,name,description,owner_id,"open",self._now()))
        with self._db() as c: return self._row(c.execute("SELECT * FROM controls WHERE control_id=?",(cid,)).fetchone())

    def assess_risk(self,tenant_id,workspace_id,title,likelihood,impact,obligation_id=None,treatment="",owner_id=None):
        likelihood=max(1,min(int(likelihood),5)); impact=max(1,min(int(impact),5)); score=likelihood*impact
        level="critical" if score>=20 else "high" if score>=12 else "medium" if score>=6 else "low"
        now=self._now(); rid=self._id("RSK")
        with self._db() as c: c.execute("INSERT INTO risks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,str(tenant_id),str(workspace_id),obligation_id,title,likelihood,impact,score,level,"open",treatment,owner_id,now,now))
        return self.get_risk(tenant_id,workspace_id,rid)

    def get_risk(self,tenant_id,workspace_id,risk_id):
        with self._db() as c: return self._row(c.execute("SELECT * FROM risks WHERE risk_id=? AND tenant_id=? AND workspace_id=?",(risk_id,str(tenant_id),str(workspace_id))).fetchone())

    def add_evidence(self,tenant_id,workspace_id,title,reference="",obligation_id=None,control_id=None):
        if obligation_id and not self.get_obligation(tenant_id,workspace_id,obligation_id): raise ValueError("obligation_not_found")
        eid=self._id("EVD")
        with self._db() as c: c.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?)",(eid,str(tenant_id),str(workspace_id),obligation_id,control_id,title,reference,0,None,None,self._now()))
        with self._db() as c: return self._row(c.execute("SELECT * FROM evidence WHERE evidence_id=?",(eid,)).fetchone())

    def verify_evidence(self,tenant_id,workspace_id,evidence_id,verifier):
        if not verifier: raise ValueError("verifier_required")
        with self._db() as c:
            row=c.execute("SELECT * FROM evidence WHERE evidence_id=? AND tenant_id=? AND workspace_id=?",(evidence_id,str(tenant_id),str(workspace_id))).fetchone()
            if not row: raise ValueError("evidence_not_found")
            c.execute("UPDATE evidence SET verified=1,verified_by=?,verified_at=? WHERE evidence_id=?",(verifier,self._now(),evidence_id))
        with self._db() as c: return self._row(c.execute("SELECT * FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone())

    def add_action(self,tenant_id,workspace_id,title,risk_id=None,obligation_id=None,owner_id=None,due_at=None):
        if risk_id and not self.get_risk(tenant_id,workspace_id,risk_id): raise ValueError("risk_not_found")
        aid=self._id("ACT"); now=self._now()
        with self._db() as c: c.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?,?,?)",(aid,str(tenant_id),str(workspace_id),risk_id,obligation_id,title,owner_id,due_at,"open",now,now))
        with self._db() as c: return self._row(c.execute("SELECT * FROM actions WHERE action_id=?",(aid,)).fetchone())

    def matrix(self,tenant_id,workspace_id):
        with self._db() as c:
            scope=(str(tenant_id),str(workspace_id))
            return {"obligations":[dict(x) for x in c.execute("SELECT * FROM obligations WHERE tenant_id=? AND workspace_id=? ORDER BY name",scope)],
                    "risks":[dict(x) for x in c.execute("SELECT * FROM risks WHERE tenant_id=? AND workspace_id=? ORDER BY score DESC",scope)],
                    "actions":[dict(x) for x in c.execute("SELECT * FROM actions WHERE tenant_id=? AND workspace_id=? ORDER BY title",scope)],
                    "evidence":[dict(x) for x in c.execute("SELECT * FROM evidence WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC",scope)]}

    def update_action_status(self, tenant_id, workspace_id, action_id, status, changed_by="system"):
        allowed = ("open", "in_progress", "completed", "closed", "cancelled")
        if status not in allowed:
            raise ValueError("invalid_action_status")
        with self._db() as c:
            row = c.execute("SELECT * FROM actions WHERE action_id=? AND tenant_id=? AND workspace_id=?", (action_id, str(tenant_id), str(workspace_id))).fetchone()
            if not row:
                raise ValueError("action_not_found")
            c.execute("UPDATE actions SET status=?,updated_at=? WHERE action_id=? AND tenant_id=? AND workspace_id=?", (status, self._now(), action_id, str(tenant_id), str(workspace_id)))
        return self._row(c.execute("SELECT * FROM actions WHERE action_id=?", (action_id,)).fetchone()) if False else self._get_action(tenant_id, workspace_id, action_id)

    def _get_action(self, tenant_id, workspace_id, action_id):
        with self._db() as c:
            return self._row(c.execute("SELECT * FROM actions WHERE action_id=? AND tenant_id=? AND workspace_id=?", (action_id, str(tenant_id), str(workspace_id))).fetchone())

    def update_obligation_status(self, tenant_id, workspace_id, obligation_id, status):
        if status not in self.STATUSES:
            raise ValueError("invalid_obligation_status")
        with self._db() as c:
            row = c.execute("SELECT * FROM obligations WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",
                            (obligation_id, str(tenant_id), str(workspace_id))).fetchone()
            if not row:
                raise ValueError("obligation_not_found")
            c.execute("UPDATE obligations SET status=?,updated_at=? WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",
                      (status, self._now(), obligation_id, str(tenant_id), str(workspace_id)))
        return self.get_obligation(tenant_id, workspace_id, obligation_id)

    def update_control_status(self, tenant_id, workspace_id, control_id, status):
        allowed = ("open", "in_progress", "effective", "ineffective", "closed")
        if status not in allowed:
            raise ValueError("invalid_control_status")
        with self._db() as c:
            row = c.execute("SELECT * FROM controls WHERE control_id=? AND tenant_id=? AND workspace_id=?",
                            (control_id, str(tenant_id), str(workspace_id))).fetchone()
            if not row:
                raise ValueError("control_not_found")
            c.execute("UPDATE controls SET status=? WHERE control_id=? AND tenant_id=? AND workspace_id=?",
                      (status, control_id, str(tenant_id), str(workspace_id)))
            return self._row(c.execute("SELECT * FROM controls WHERE control_id=?", (control_id,)).fetchone())

    def update_risk_status(self, tenant_id, workspace_id, risk_id, status):
        if status not in ("open", "in_progress", "mitigated", "accepted", "closed"):
            raise ValueError("invalid_risk_status")
        with self._db() as c:
            row = c.execute("SELECT * FROM risks WHERE risk_id=? AND tenant_id=? AND workspace_id=?",
                            (risk_id, str(tenant_id), str(workspace_id))).fetchone()
            if not row:
                raise ValueError("risk_not_found")
            c.execute("UPDATE risks SET status=?,updated_at=? WHERE risk_id=? AND tenant_id=? AND workspace_id=?",
                      (status, self._now(), risk_id, str(tenant_id), str(workspace_id)))
            return self._row(c.execute("SELECT * FROM risks WHERE risk_id=?", (risk_id,)).fetchone())

    def link_evidence(self, tenant_id, workspace_id, evidence_id, obligation_id=None, control_id=None):
        with self._db() as c:
            evidence = c.execute("SELECT * FROM evidence WHERE evidence_id=? AND tenant_id=? AND workspace_id=?",
                                 (evidence_id, str(tenant_id), str(workspace_id))).fetchone()
            if not evidence:
                raise ValueError("evidence_not_found")
            if obligation_id and not c.execute("SELECT 1 FROM obligations WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",
                                                (obligation_id, str(tenant_id), str(workspace_id))).fetchone():
                raise ValueError("obligation_not_found")
            if control_id and not c.execute("SELECT 1 FROM controls WHERE control_id=? AND tenant_id=? AND workspace_id=?",
                                             (control_id, str(tenant_id), str(workspace_id))).fetchone():
                raise ValueError("control_not_found")
            c.execute("UPDATE evidence SET obligation_id=COALESCE(?,obligation_id), control_id=COALESCE(?,control_id) WHERE evidence_id=? AND tenant_id=? AND workspace_id=?",
                      (obligation_id, control_id, evidence_id, str(tenant_id), str(workspace_id)))
            return self._row(c.execute("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)).fetchone())

    def matrix_v2(self, tenant_id, workspace_id):
        scope = (str(tenant_id), str(workspace_id))
        with self._db() as c:
            obligations = [dict(x) for x in c.execute("SELECT * FROM obligations WHERE tenant_id=? AND workspace_id=? ORDER BY name", scope)]
            controls = [dict(x) for x in c.execute("SELECT * FROM controls WHERE tenant_id=? AND workspace_id=? ORDER BY name", scope)]
            evidence = [dict(x) for x in c.execute("SELECT * FROM evidence WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC", scope)]
            risks = [dict(x) for x in c.execute("SELECT * FROM risks WHERE tenant_id=? AND workspace_id=? ORDER BY score DESC", scope)]
            actions = [dict(x) for x in c.execute("SELECT * FROM actions WHERE tenant_id=? AND workspace_id=? ORDER BY due_at, title", scope)]
        control_by_obligation = {}
        for control in controls:
            control_by_obligation.setdefault(control["obligation_id"], []).append(control)
        evidence_by_control = {}
        for item in evidence:
            evidence_by_control.setdefault(item["control_id"], []).append(item)
        risk_by_obligation = {}
        for risk in risks:
            risk_by_obligation.setdefault(risk["obligation_id"], []).append(risk)
        action_by_risk = {}
        for action in actions:
            action_by_risk.setdefault(action["risk_id"], []).append(action)
        rows = []
        for obligation in obligations:
            linked_controls = control_by_obligation.get(obligation["obligation_id"], [])
            linked_evidence = [e for e in evidence if e["obligation_id"] == obligation["obligation_id"]]
            linked_risks = risk_by_obligation.get(obligation["obligation_id"], [])
            rows.append({
                "obligation": obligation,
                "controls": linked_controls,
                "evidence": linked_evidence,
                "risks": linked_risks,
                "actions": [a for r in linked_risks for a in action_by_risk.get(r["risk_id"], [])],
                "control_coverage": bool(linked_controls),
                "evidence_coverage": bool(linked_evidence),
                "verified_evidence_coverage": any(int(e["verified"]) == 1 for e in linked_evidence),
            })
        return {"rows": rows, "unlinked_controls": [c for c in controls if not c["obligation_id"]],
                "unlinked_evidence": [e for e in evidence if not e["obligation_id"] and not e["control_id"]],
                "risks": risks, "actions": actions}

    def health(self):
        return {"status":"ok","engine":"compliance-risk","matrix_v2":True,"tenant_isolation":True,
                "risk_scale":"1-5 likelihood x 1-5 impact","evidence_verification":True,
                "remediation_tracking":True,"traceability":True}
