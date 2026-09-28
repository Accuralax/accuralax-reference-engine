import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class AgentReplanningEngine:
    """Bounded feedback-to-proposal loop. Never executes a replanned action."""
    def __init__(self, planner, executor, db_path=None, max_replans=3):
        self.planner=planner; self.executor=executor
        self.db_path=db_path or os.path.join("data","agent_replanning.sqlite3")
        self.max_replans=max(1,min(int(max_replans),10)); os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS replans(replan_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,source_plan_id TEXT,outcome TEXT,status TEXT,created_at TEXT,reason TEXT,new_plan_id TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_replans_scope ON replans(tenant_id,workspace_id,created_at)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def _count(self,t,w,p):
        with self._db() as c: return c.execute("SELECT COUNT(*) FROM replans WHERE tenant_id=? AND workspace_id=? AND source_plan_id=?",(str(t),str(w),str(p))).fetchone()[0]
    def classify(self,feedback):
        return {"failure":"execution_failure","incomplete":"approval_or_execution_incomplete","not_started":"execution_not_started","success":"completed"}.get(feedback.get("outcome"),"unknown")
    def propose(self,tenant_id,workspace_id,source_plan_id,lead=None,opportunity=None,consent_granted=False,open_tasks=0):
        feedback=self.executor.feedback(tenant_id,workspace_id,source_plan_id); category=self.classify(feedback)
        if category=="completed": return {"status":"no_replan","reason":"source_plan_completed","feedback":feedback}
        count=self._count(tenant_id,workspace_id,source_plan_id)
        if count>=self.max_replans: return {"status":"blocked","reason":"replan_budget_exhausted","feedback":feedback,"replans":count}
        client_id=str((lead or {}).get("client_id") or (opportunity or {}).get("client_id") or "unknown")
        plan=self.planner.plan(tenant_id,workspace_id,client_id,lead,opportunity,consent_granted,open_tasks,"replan:"+category+":"+str(source_plan_id))
        rid="RPL-"+uuid.uuid4().hex[:16].upper()
        with self._db() as c: c.execute("INSERT INTO replans VALUES(?,?,?,?,?,?,?,?,?)",(rid,str(tenant_id),str(workspace_id),str(source_plan_id),feedback["outcome"],"proposed",datetime.now(timezone.utc).isoformat(),category,plan["plan_id"]))
        return {"status":"proposed","replan_id":rid,"source_plan_id":source_plan_id,"new_plan_id":plan["plan_id"],"reason":category,"feedback":feedback,"plan":plan}
    def get(self,tenant_id,workspace_id,replan_id):
        with self._db() as c: row=c.execute("SELECT * FROM replans WHERE tenant_id=? AND workspace_id=? AND replan_id=?",(str(tenant_id),str(workspace_id),str(replan_id))).fetchone()
        if not row: raise ValueError("replan_not_found")
        return dict(row)
    def health(self):
        with self._db() as c: count=c.execute("SELECT COUNT(*) FROM replans").fetchone()[0]
        return {"status":"ok","engine":"agent-replanning","bounded":True,"max_replans":self.max_replans,"execution_separate":True,"replans":count}
