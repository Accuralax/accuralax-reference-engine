from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone, timedelta

class SLAEscalation:
    """Tenant-scoped SLA policies, tracked deadlines and escalation history."""
    STATES={"open","met","overdue","escalated","resolved"}
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","sla_escalation.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS policies(policy_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,target_type TEXT,target_hours REAL,escalation_hours REAL,active INTEGER,metadata TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS items(item_id TEXT PRIMARY KEY,policy_id TEXT,tenant_id TEXT,workspace_id TEXT,reference_type TEXT,reference_id TEXT,owner_id TEXT,status TEXT,due_at TEXT,escalated_at TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,item_id TEXT,tenant_id TEXT,workspace_id TEXT,event_type TEXT,actor_id TEXT,metadata TEXT,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc)
    def define_policy(self,t,w,name,target_type,target_hours,escalation_hours=0,metadata=None):
        t,w=self.scope(t,w); pid="SLA-"+uuid.uuid4().hex[:12].upper(); now=self.now().isoformat()
        with self.db() as c:c.execute("INSERT INTO policies VALUES(?,?,?,?,?,?,?,?,?,?)",(pid,t,w,name,target_type,float(target_hours),float(escalation_hours),1,json.dumps(metadata or {}),now))
        return self.policy(t,w,pid)
    def policy(self,t,w,pid):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT policy_id,name,target_type,target_hours,escalation_hours,active,metadata,created_at FROM policies WHERE policy_id=? AND tenant_id=? AND workspace_id=?",(pid,t,w)).fetchone()
        if not r:return None
        out=dict(zip(("policy_id","name","target_type","target_hours","escalation_hours","active","metadata","created_at"),r)); out["metadata"]=json.loads(out["metadata"] or "{}"); return out
    def start(self,t,w,pid,reference_type,reference_id,owner_id=""):
        t,w=self.scope(t,w); p=self.policy(t,w,pid)
        if not p:return {"allowed":False,"reason":"policy_not_found"}
        now=self.now(); due=now+timedelta(hours=p["target_hours"]); iid="SLI-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(iid,pid,t,w,reference_type,reference_id,owner_id,"open",due.isoformat(),None,now.isoformat(),now.isoformat()))
            c.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",(uuid.uuid4().hex,iid,t,w,"started","system",json.dumps({}),now.isoformat()))
        return self.get(t,w,iid)
    def get(self,t,w,item_id):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT item_id,policy_id,reference_type,reference_id,owner_id,status,due_at,escalated_at,created_at,updated_at FROM items WHERE item_id=? AND tenant_id=? AND workspace_id=?",(item_id,t,w)).fetchone()
        if not r:return None
        return dict(zip(("item_id","policy_id","reference_type","reference_id","owner_id","status","due_at","escalated_at","created_at","updated_at"),r))
    def evaluate(self,t,w,item_id,now=None):
        t,w=self.scope(t,w); now=now or self.now(); item=self.get(t,w,item_id)
        if not item:return {"allowed":False,"reason":"item_not_found"}
        if item["status"] in {"met","resolved"}:return item
        due=datetime.fromisoformat(item["due_at"])
        p=self.policy(t,w,item["policy_id"]); status=item["status"]
        if now>=due and status=="open":
            status="overdue"
            if p["escalation_hours"]<=0: status="escalated"
        if status=="overdue" and p["escalation_hours"]>0 and now>=due+timedelta(hours=p["escalation_hours"]): status="escalated"
        if status!=item["status"]:
            with self.db() as c:
                esc=now.isoformat() if status=="escalated" else item["escalated_at"]
                c.execute("UPDATE items SET status=?,escalated_at=?,updated_at=? WHERE item_id=? AND tenant_id=? AND workspace_id=?",(status,esc,now.isoformat(),item_id,t,w))
                c.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",(uuid.uuid4().hex,item_id,t,w,status,"system",json.dumps({}),now.isoformat()))
        return self.get(t,w,item_id)
    def resolve(self,t,w,item_id,met=True,actor_id="system"):
        t,w=self.scope(t,w); item=self.get(t,w,item_id)
        if not item:return {"allowed":False,"reason":"item_not_found"}
        status="met" if met else "resolved"; now=self.now().isoformat()
        with self.db() as c:
            c.execute("UPDATE items SET status=?,updated_at=? WHERE item_id=? AND tenant_id=? AND workspace_id=?",(status,now,item_id,t,w))
            c.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",(uuid.uuid4().hex,item_id,t,w,status,actor_id,json.dumps({}),now))
        return self.get(t,w,item_id)
    def history(self,t,w,item_id=None):
        t,w=self.scope(t,w); q="SELECT event_id,item_id,event_type,actor_id,metadata,created_at FROM events WHERE tenant_id=? AND workspace_id=?"; args=[t,w]
        if item_id:q+=" AND item_id=?"; args.append(item_id)
        q+=" ORDER BY created_at DESC"
        with self.db() as c: rows=c.execute(q,args).fetchall()
        return [dict(zip(("event_id","item_id","event_type","actor_id","metadata","created_at"),r)) for r in rows]
    def health(self):
        with self.db() as c:a=c.execute("SELECT COUNT(*) FROM policies").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM items").fetchone()[0]; e=c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"status":"ok","policies":a,"items":b,"events":e,"tenant_scoped":True,"escalation":True}
