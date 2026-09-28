from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from contextlib import contextmanager

class TaskAssignment:
    """Durable tenant-scoped work queue with assignment, status and priority controls."""
    STATUSES={"open","in_progress","blocked","completed","cancelled"}
    PRIORITIES={"low","normal","high","urgent"}
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","task_assignment.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,title TEXT,description TEXT,status TEXT,priority TEXT,assignee_id TEXT,created_by TEXT,due_at TEXT,reference_type TEXT,reference_id TEXT,metadata TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS task_history(history_id TEXT PRIMARY KEY,task_id TEXT,tenant_id TEXT,workspace_id TEXT,actor_id TEXT,event TEXT,details TEXT,created_at TEXT)")
    @contextmanager
    def db(self):
        c = sqlite3.connect(self.db_path)
        try:
            yield c
            c.commit()
        finally:
            c.close()
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def create(self,t,w,title,created_by,description="",priority="normal",assignee_id=None,due_at=None,reference_type=None,reference_id=None,metadata=None):
        t,w=self.scope(t,w)
        if priority not in self.PRIORITIES: raise ValueError("invalid_priority")
        task_id="TASK-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(task_id,t,w,title,description,"open",priority,assignee_id,created_by,due_at,reference_type,reference_id,json.dumps(metadata or {}),now,now))
            self._history(c,task_id,t,w,created_by,"created",{"priority":priority,"assignee_id":assignee_id})
        return self.get(t,w,task_id)
    def get(self,t,w,task_id):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT * FROM tasks WHERE task_id=? AND tenant_id=? AND workspace_id=?",(task_id,t,w)).fetchone()
        if not r:return None
        keys=("task_id","tenant_id","workspace_id","title","description","status","priority","assignee_id","created_by","due_at","reference_type","reference_id","metadata","created_at","updated_at")
        out=dict(zip(keys,r)); out["metadata"]=json.loads(out["metadata"]); return out
    def assign(self,t,w,task_id,assignee_id,actor_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            r=c.execute("SELECT status FROM tasks WHERE task_id=? AND tenant_id=? AND workspace_id=?",(task_id,t,w)).fetchone()
            if not r: raise KeyError("task_not_found")
            if r[0] in {"completed","cancelled"}: raise ValueError("task_immutable")
            now=self.now(); c.execute("UPDATE tasks SET assignee_id=?,updated_at=? WHERE task_id=? AND tenant_id=? AND workspace_id=?",(assignee_id,now,task_id,t,w)); self._history(c,task_id,t,w,actor_id,"assigned",{"assignee_id":assignee_id})
        return self.get(t,w,task_id)
    def transition(self,t,w,task_id,status,actor_id):
        t,w=self.scope(t,w)
        if status not in self.STATUSES: raise ValueError("invalid_status")
        with self.db() as c:
            r=c.execute("SELECT status FROM tasks WHERE task_id=? AND tenant_id=? AND workspace_id=?",(task_id,t,w)).fetchone()
            if not r: raise KeyError("task_not_found")
            if r[0] in {"completed","cancelled"} and status!=r[0]: raise ValueError("task_immutable")
            now=self.now(); c.execute("UPDATE tasks SET status=?,updated_at=? WHERE task_id=? AND tenant_id=? AND workspace_id=?",(status,now,task_id,t,w)); self._history(c,task_id,t,w,actor_id,"status_changed",{"status":status})
        return self.get(t,w,task_id)
    def list(self,t,w,status=None,assignee_id=None,limit=100):
        t,w=self.scope(t,w); q="SELECT task_id FROM tasks WHERE tenant_id=? AND workspace_id=?"; args=[t,w]
        if status:q+=" AND status=?"; args.append(status)
        if assignee_id:q+=" AND assignee_id=?"; args.append(assignee_id)
        q+=" ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,created_at DESC LIMIT ?"; args.append(int(limit))
        with self.db() as c:ids=[x[0] for x in c.execute(q,args).fetchall()]
        return [self.get(t,w,i) for i in ids]
    def history(self,t,w,task_id=None,limit=100):
        t,w=self.scope(t,w); q="SELECT history_id,task_id,actor_id,event,details,created_at FROM task_history WHERE tenant_id=? AND workspace_id=?"; args=[t,w]
        if task_id:q+=" AND task_id=?"; args.append(task_id)
        q+=" ORDER BY created_at DESC LIMIT ?"; args.append(int(limit))
        with self.db() as c:rows=c.execute(q,args).fetchall()
        out=[]
        for r in rows:
            d=dict(zip(("history_id","task_id","actor_id","event","details","created_at"),r)); d["details"]=json.loads(d["details"]); out.append(d)
        return out
    def _history(self,c,task_id,t,w,actor,event,details):
        c.execute("INSERT INTO task_history VALUES(?,?,?,?,?,?,?,?)",("H-"+uuid.uuid4().hex[:12].upper(),task_id,t,w,str(actor or "system"),event,json.dumps(details),self.now()))
    def health(self):
        with self.db() as c:a=c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
        return {"status":"ok","tasks":a,"history":b,"tenant_scoped":True,"statuses":sorted(self.STATUSES),"priorities":sorted(self.PRIORITIES)}
