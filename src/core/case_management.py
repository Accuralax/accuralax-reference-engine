from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone

class CaseManagement:
    """Durable, tenant-scoped workflow and case lifecycle engine."""
    STATES={"open","in_progress","waiting","resolved","closed","cancelled"}
    PRIORITIES={"low","normal","high","urgent"}

    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","case_management.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,title TEXT,case_type TEXT,priority TEXT,state TEXT,assignee TEXT,created_by TEXT,created_at TEXT,updated_at TEXT,due_at TEXT,metadata TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS case_events(event_id TEXT PRIMARY KEY,case_id TEXT,tenant_id TEXT,workspace_id TEXT,event_type TEXT,actor_id TEXT,payload TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS case_tasks(task_id TEXT PRIMARY KEY,case_id TEXT,tenant_id TEXT,workspace_id TEXT,title TEXT,assignee TEXT,state TEXT,due_at TEXT,created_at TEXT,updated_at TEXT)")

    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()

    def create_case(self,t,w,title,case_type="general",priority="normal",created_by="system",assignee="",due_at=None,metadata=None):
        t,w=self.scope(t,w)
        if not title.strip(): return {"allowed":False,"reason":"case_title_required"}
        if priority not in self.PRIORITIES: return {"allowed":False,"reason":"invalid_priority"}
        cid="CASE-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            c.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,t,w,title,case_type,priority,"open",assignee,created_by,now,now,due_at,json.dumps(metadata or {})))
            self._event(c,cid,t,w,"created",created_by,{"state":"open"})
        return self.get_case(t,w,cid)

    def get_case(self,t,w,case_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            row=c.execute("SELECT case_id,title,case_type,priority,state,assignee,created_by,created_at,updated_at,due_at,metadata FROM cases WHERE case_id=? AND tenant_id=? AND workspace_id=?",(case_id,t,w)).fetchone()
        if not row: return None
        keys=("case_id","title","case_type","priority","state","assignee","created_by","created_at","updated_at","due_at","metadata")
        out=dict(zip(keys,row)); out["metadata"]=json.loads(out["metadata"] or "{}")
        return out

    def transition(self,t,w,case_id,state,actor_id="system",reason=""):
        t,w=self.scope(t,w)
        if state not in self.STATES: return {"allowed":False,"reason":"invalid_state"}
        with self.db() as c:
            row=c.execute("SELECT state FROM cases WHERE case_id=? AND tenant_id=? AND workspace_id=?",(case_id,t,w)).fetchone()
            if not row: return {"allowed":False,"reason":"case_not_found"}
            current=row[0]
            if current=="closed" and state!="closed": return {"allowed":False,"reason":"closed_case_immutable"}
            now=self.now()
            c.execute("UPDATE cases SET state=?,updated_at=? WHERE case_id=? AND tenant_id=? AND workspace_id=?",(state,now,case_id,t,w))
            self._event(c,case_id,t,w,"state_changed",actor_id,{"from":current,"to":state,"reason":reason})
        return self.get_case(t,w,case_id)

    def assign(self,t,w,case_id,assignee,actor_id="system"):
        t,w=self.scope(t,w)
        with self.db() as c:
            if not c.execute("SELECT 1 FROM cases WHERE case_id=? AND tenant_id=? AND workspace_id=?",(case_id,t,w)).fetchone(): return {"allowed":False,"reason":"case_not_found"}
            now=self.now()
            c.execute("UPDATE cases SET assignee=?,updated_at=? WHERE case_id=? AND tenant_id=? AND workspace_id=?",(assignee,now,case_id,t,w))
            self._event(c,case_id,t,w,"assigned",actor_id,{"assignee":assignee})
        return self.get_case(t,w,case_id)

    def add_task(self,t,w,case_id,title,assignee="",due_at=None):
        t,w=self.scope(t,w)
        if not self.get_case(t,w,case_id): return {"allowed":False,"reason":"case_not_found"}
        tid="TASK-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            c.execute("INSERT INTO case_tasks VALUES(?,?,?,?,?,?,?,?,?,?)",(tid,case_id,t,w,title,assignee,"open",due_at,now,now))
        return {"task_id":tid,"case_id":case_id,"title":title,"state":"open","assignee":assignee,"due_at":due_at}

    def update_task(self,t,w,task_id,state,assignee=None):
        t,w=self.scope(t,w)
        if state not in {"open","in_progress","blocked","done","cancelled"}: return {"allowed":False,"reason":"invalid_task_state"}
        with self.db() as c:
            row=c.execute("SELECT task_id,case_id,assignee FROM case_tasks WHERE task_id=? AND tenant_id=? AND workspace_id=?",(task_id,t,w)).fetchone()
            if not row: return {"allowed":False,"reason":"task_not_found"}
            new_assignee=row[2] if assignee is None else assignee
            c.execute("UPDATE case_tasks SET state=?,assignee=?,updated_at=? WHERE task_id=? AND tenant_id=? AND workspace_id=?",(state,new_assignee,self.now(),task_id,t,w))
        return {"task_id":task_id,"case_id":row[1],"state":state,"assignee":new_assignee}

    def history(self,t,w,case_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            rows=c.execute("SELECT event_id,event_type,actor_id,payload,created_at FROM case_events WHERE case_id=? AND tenant_id=? AND workspace_id=? ORDER BY created_at",(case_id,t,w)).fetchall()
        return [{"event_id":a,"event_type":b,"actor_id":c,"payload":json.loads(d or "{}"),"created_at":e} for a,b,c,d,e in rows]

    def _event(self,c,cid,t,w,event_type,actor,payload):
        c.execute("INSERT INTO case_events VALUES(?,?,?,?,?,?,?,?)",("CE-"+uuid.uuid4().hex[:12].upper(),cid,t,w,event_type,actor,json.dumps(payload),self.now()))

    def health(self):
        with self.db() as c:
            cases=c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
            tasks=c.execute("SELECT COUNT(*) FROM case_tasks").fetchone()[0]
            events=c.execute("SELECT COUNT(*) FROM case_events").fetchone()[0]
        return {"status":"ok","cases":cases,"tasks":tasks,"events":events,"tenant_scoped":True,"durable":True}
