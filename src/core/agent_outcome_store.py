import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class AgentOutcomeStore:
    """Durable, tenant-scoped ledger of agent action outcomes."""
    OUTCOMES = ("completed", "failed", "blocked", "pending", "running", "already_executed")
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","agent_outcomes.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS action_outcomes(
                outcome_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                agent_id TEXT NOT NULL, plan_id TEXT NOT NULL, decision_id TEXT NOT NULL,
                position INTEGER NOT NULL, action TEXT NOT NULL, outcome TEXT NOT NULL,
                reason_code TEXT NOT NULL, reason TEXT, context_fingerprint TEXT,
                result_json TEXT, created_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_scope ON action_outcomes(tenant_id,workspace_id,created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_context ON action_outcomes(tenant_id,workspace_id,context_fingerprint,action)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()
    def record(self,tenant_id,workspace_id,agent_id,plan_id,decision_id,position,action,outcome,reason_code="unknown",reason="",context_fingerprint="",result=None):
        if outcome not in self.OUTCOMES: raise ValueError("invalid_outcome")
        oid="AO-"+uuid.uuid4().hex[:16].upper()
        now=datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("INSERT INTO action_outcomes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (oid,str(tenant_id),str(workspace_id),str(agent_id),str(plan_id),str(decision_id),int(position),
                 str(action),str(outcome),str(reason_code),str(reason or ""),str(context_fingerprint or ""),
                 json.dumps(result or {},default=str),now))
        return {"outcome_id":oid,"status":"recorded"}
    def query(self,tenant_id,workspace_id,action=None,context_fingerprint=None,limit=100):
        sql="SELECT * FROM action_outcomes WHERE tenant_id=? AND workspace_id=?"
        args=[str(tenant_id),str(workspace_id)]
        if action is not None: sql+=" AND action=?"; args.append(str(action))
        if context_fingerprint is not None: sql+=" AND context_fingerprint=?"; args.append(str(context_fingerprint))
        sql+=" ORDER BY created_at DESC LIMIT ?"; args.append(max(1,min(int(limit),500)))
        with self._db() as c: rows=c.execute(sql,args).fetchall()
        return [dict(r) for r in rows]
    def stats(self,tenant_id,workspace_id,action=None,context_fingerprint=None):
        rows=self.query(tenant_id,workspace_id,action,context_fingerprint,500)
        stats={}
        for r in rows:
            key=r["action"]; s=stats.setdefault(key,{"total":0,"completed":0,"failed":0,"blocked":0})
            s["total"]+=1
            s[r["outcome"]]=s.get(r["outcome"],0)+1
        return stats
    def health(self):
        with self._db() as c: count=c.execute("SELECT COUNT(*) FROM action_outcomes").fetchone()[0]
        return {"status":"ok","engine":"agent-outcome-store","records":count,"tenant_scoped":True}
