from __future__ import annotations
import json, os, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class WorkflowAutomation:
    """Durable tenant-scoped workflow definitions and bounded execution plans."""
    STATES={"queued","running","completed","failed","blocked"}
    def __init__(self, db_path=None, max_steps=20):
        self.db_path=db_path or os.path.join("data","workflow_automation.sqlite3")
        self.max_steps=max(1,min(int(max_steps),50))
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS workflows(workflow_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,trigger_type TEXT,steps TEXT,active INTEGER,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,workflow_id TEXT,tenant_id TEXT,workspace_id TEXT,status TEXT,current_step INTEGER,result TEXT,created_at TEXT,updated_at TEXT)")
    @contextmanager
    def db(self):
        c = sqlite3.connect(self.db_path, timeout=15.0)
        c.execute('PRAGMA busy_timeout=15000')
        try:
            yield c
            c.commit()
        finally:
            c.close()
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def define(self,t,w,name,trigger_type,steps):
        t,w=self.scope(t,w)
        if not isinstance(steps,list) or not steps or len(steps)>self.max_steps:return {"allowed":False,"reason":"invalid_step_count"}
        wid="WF-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:c.execute("INSERT INTO workflows VALUES(?,?,?,?,?,?,?,?,?)",(wid,t,w,name,trigger_type,json.dumps(steps),1,now,now))
        return self.get(t,w,wid)
    def get(self,t,w,wid):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT workflow_id,name,trigger_type,steps,active,created_at,updated_at FROM workflows WHERE workflow_id=? AND tenant_id=? AND workspace_id=?",(wid,t,w)).fetchone()
        if not r:return None
        out=dict(zip(("workflow_id","name","trigger_type","steps","active","created_at","updated_at"),r)); out["steps"]=json.loads(out["steps"]); return out
    def start(self,t,w,wid,context=None):
        t,w=self.scope(t,w); wf=self.get(t,w,wid)
        if not wf:return {"allowed":False,"reason":"workflow_not_found"}
        run="WRUN-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:c.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)",(run,wid,t,w,"queued",0,json.dumps({"context":context or {}, "steps":[]}),now,now))
        return self.get_run(t,w,run)
    def get_run(self,t,w,run_id):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT run_id,workflow_id,status,current_step,result,created_at,updated_at FROM runs WHERE run_id=? AND tenant_id=? AND workspace_id=?",(run_id,t,w)).fetchone()
        if not r:return None
        out=dict(zip(("run_id","workflow_id","status","current_step","result","created_at","updated_at"),r)); out["result"]=json.loads(out["result"] or "{}"); return out
    def execute(self,t,w,run_id,executor=None,approved=False):
        t,w=self.scope(t,w); run=self.get_run(t,w,run_id)
        if not run:return {"allowed":False,"reason":"run_not_found"}
        wf=self.get(t,w,run["workflow_id"])
        if not wf:return {"allowed":False,"reason":"workflow_not_found"}
        steps=wf["steps"]
        with self.db() as c:c.execute("UPDATE runs SET status=?,updated_at=? WHERE run_id=? AND tenant_id=? AND workspace_id=?",( "running",self.now(),run_id,t,w))
        results=[]
        try:
            for i,step in enumerate(steps):
                if step.get("requires_approval",False) and not approved:
                    status="blocked"; results.append({"step":i,"status":"blocked","reason":"approval_required"}); break
                if executor is None:
                    results.append({"step":i,"status":"planned","action":step.get("action")}); continue
                value=executor(step)
                results.append({"step":i,"status":"completed","result":value})
            else: status="completed"
            with self.db() as c:c.execute("UPDATE runs SET status=?,current_step=?,result=?,updated_at=? WHERE run_id=? AND tenant_id=? AND workspace_id=?",(status,len(results),json.dumps({"steps":results}),self.now(),run_id,t,w))
            return self.get_run(t,w,run_id)
        except Exception as exc:
            with self.db() as c:c.execute("UPDATE runs SET status=?,current_step=?,result=?,updated_at=? WHERE run_id=? AND tenant_id=? AND workspace_id=?",( "failed",len(results),json.dumps({"steps":results,"error":str(exc)}),self.now(),run_id,t,w))
            return self.get_run(t,w,run_id)
    def history(self,t,w,workflow_id=None):
        t,w=self.scope(t,w); q="SELECT run_id,workflow_id,status,current_step,created_at,updated_at FROM runs WHERE tenant_id=? AND workspace_id=?"; args=[t,w]
        if workflow_id:q+=" AND workflow_id=?"; args.append(workflow_id)
        q+=" ORDER BY created_at DESC"
        with self.db() as c:rows=c.execute(q,args).fetchall()
        return [dict(zip(("run_id","workflow_id","status","current_step","created_at","updated_at"),r)) for r in rows]
    def health(self):
        with self.db() as c:a=c.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        return {"status":"ok","workflows":a,"runs":b,"tenant_scoped":True,"bounded_steps":self.max_steps}
