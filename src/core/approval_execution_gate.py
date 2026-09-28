from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from contextlib import contextmanager

class ApprovalExecutionGate:
    """Durable approval boundary for operational actions with audit-friendly decisions."""
    def __init__(self, approval_gateway=None, governance=None, audit=None, db_path=None):
        self.approvals=approval_gateway; self.governance=governance; self.audit=audit
        self.db_path=db_path or os.path.join("data","approval_execution_gate.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS decisions(decision_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,run_id TEXT,action TEXT,risk TEXT,status TEXT,reason TEXT,approved_by TEXT,trace_id TEXT,correlation_id TEXT,created_at TEXT,updated_at TEXT,UNIQUE(tenant_id,workspace_id,run_id,action))")
            cols={r[1] for r in c.execute("PRAGMA table_info(decisions)").fetchall()}
            for col in ("trace_id", "correlation_id"):
                if col not in cols: c.execute(f"ALTER TABLE decisions ADD COLUMN {col} TEXT")
    @contextmanager
    def db(self):
        c = sqlite3.connect(self.db_path)
        try:
            yield c
            c.commit()
        finally:
            c.close()
    def now(self): return datetime.now(timezone.utc).isoformat()
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def _audit(self,t,w,actor,event_type,status,decision_id=None,run_id=None,action=None,trace_id=None,correlation_id=None,metadata=None):
        if not self.audit:return
        try:
            self.audit.record(t,w,actor,event_type,source="approval",status=status,
                              entity_type="approval_decision",entity_id=decision_id,
                              reference_id=run_id,trace_id=trace_id,correlation_id=correlation_id,
                              metadata=dict(metadata or {},action=action) if action else (metadata or {}))
        except Exception: pass

    def request(self,t,w,run_id,action,risk="normal",actor_id="system",requires_approval=None,trace_id=None,correlation_id=None):
        t,w=self.scope(t,w)
        risk=str(risk or "normal").lower()
        needs=requires_approval if requires_approval is not None else risk in {"high","critical","external","destructive"}
        with self.db() as c:
            old=c.execute("SELECT decision_id,status,reason,approved_by FROM decisions WHERE tenant_id=? AND workspace_id=? AND run_id=? AND action=?",(t,w,run_id,action)).fetchone()
        if old:return {"decision_id":old[0],"status":old[1],"reason":old[2],"approved_by":old[3]}
        did="DEC-"+uuid.uuid4().hex[:12].upper(); status="pending_approval" if needs else "approved"; reason="approval_required" if needs else "low_risk"
        with self.db() as c:c.execute("INSERT INTO decisions(decision_id,tenant_id,workspace_id,run_id,action,risk,status,reason,approved_by,trace_id,correlation_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(did,t,w,run_id,action,risk,status,reason,None,trace_id,correlation_id,self.now(),self.now()))
        self._audit(t,w,actor_id,"approval.requested",status,did,run_id,action,trace_id,correlation_id,{"risk":risk,"requires_approval":needs})
        return {"decision_id":did,"status":status,"reason":reason,"run_id":run_id,"action":action}
    def approve(self,t,w,decision_id,approved_by,approved=True,reason="",trace_id=None,correlation_id=None):
        t,w=self.scope(t,w)
        with self.db() as c:
            r=c.execute("SELECT run_id,action,status FROM decisions WHERE decision_id=? AND tenant_id=? AND workspace_id=?",(decision_id,t,w)).fetchone()
            if not r: raise KeyError("decision_not_found")
            status="approved" if approved else "rejected"; now=self.now()
            c.execute("UPDATE decisions SET status=?,reason=?,approved_by=?,updated_at=? WHERE decision_id=? AND tenant_id=? AND workspace_id=?",(status,reason or status,approved_by,now,decision_id,t,w))
        if self.audit:
            try:self.audit.record(t,w,approved_by,"approval.decision",source="approval",status=status,entity_type="approval_decision",entity_id=decision_id,reference_id=r[0],trace_id=trace_id,correlation_id=correlation_id,metadata={"action":r[1],"reason":reason})
            except Exception: pass
        return {"decision_id":decision_id,"run_id":r[0],"action":r[1],"status":status,"approved_by":approved_by}
    def can_execute(self,t,w,run_id,action,actor_id="system",trace_id=None,correlation_id=None):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT decision_id,status,reason FROM decisions WHERE tenant_id=? AND workspace_id=? AND run_id=? AND action=?",(t,w,run_id,action)).fetchone()
        if not r:
            self._audit(t,w,actor_id,"approval.execution_denied","denied",run_id=run_id,action=action,trace_id=trace_id,correlation_id=correlation_id,metadata={"reason":"approval_decision_missing"})
            return {"allowed":False,"reason":"approval_decision_missing"}
        allowed=r[1]=="approved"
        self._audit(t,w,actor_id,"approval.execution_allowed" if allowed else "approval.execution_denied","allowed" if allowed else "denied",r[0],run_id,action,trace_id,correlation_id,{"reason":r[2]})
        return {"allowed":allowed,"decision_id":r[0],"status":r[1],"reason":r[2]}
    def history(self,t,w,limit=100):
        t,w=self.scope(t,w)
        with self.db() as c:rows=c.execute("SELECT decision_id,run_id,action,risk,status,reason,approved_by,trace_id,correlation_id,created_at,updated_at FROM decisions WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",(t,w,int(limit))).fetchall()
        return [dict(zip(("decision_id","run_id","action","risk","status","reason","approved_by","trace_id","correlation_id","created_at","updated_at"),r)) for r in rows]
    def health(self):
        with self.db() as c:n=c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        return {"status":"ok","decisions":n,"tenant_scoped":True,"approval_boundary":True,"audit_integrated":bool(self.audit)}
