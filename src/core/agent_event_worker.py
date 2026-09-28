import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


class AgentEventWorker:
    """Durable, bounded polling worker for the autonomous agent loop."""
    def __init__(self, loop, event_bus=None, db_path=None, batch_size=10, lease_seconds=60):
        self.loop=loop
        self.events=event_bus or loop.events
        self.db_path=db_path or os.path.join("data","agent_event_worker.sqlite3")
        self.batch_size=max(1,min(int(batch_size),50)); self.lease_seconds=max(10,min(int(lease_seconds),600))
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS worker_state(tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,status TEXT NOT NULL,last_run_id TEXT,last_started_at TEXT,last_finished_at TEXT,lease_until TEXT,PRIMARY KEY(tenant_id,workspace_id))")
            c.execute("CREATE TABLE IF NOT EXISTS worker_runs(run_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,status TEXT,event_count INTEGER,started_at TEXT,finished_at TEXT,error TEXT)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def _now(self): return datetime.now(timezone.utc)
    def _claim(self,t,w):
        now=self._now(); lease=now.timestamp()+self.lease_seconds
        with self._db() as c:
            row=c.execute("SELECT lease_until,status FROM worker_state WHERE tenant_id=? AND workspace_id=?",(str(t),str(w))).fetchone()
            if row and row["lease_until"]:
                try:
                    if datetime.fromisoformat(row["lease_until"]).timestamp()>now.timestamp(): return False
                except ValueError: pass
            c.execute("INSERT INTO worker_state(tenant_id,workspace_id,status,last_started_at,lease_until) VALUES(?,?,?,?,?) ON CONFLICT(tenant_id,workspace_id) DO UPDATE SET status=excluded.status,last_started_at=excluded.last_started_at,lease_until=excluded.lease_until",(str(t),str(w),"running",now.isoformat(),datetime.fromtimestamp(lease,timezone.utc).isoformat()))
        return True
    def run_once(self,tenant_id,workspace_id,limit=None):
        if not self._claim(tenant_id,workspace_id): return {"status":"leased","processed":0}
        run_id="WRK-"+uuid.uuid4().hex[:16].upper(); started=self._now().isoformat(); limit=min(self.batch_size,max(1,int(limit or self.batch_size)))
        with self._db() as c: c.execute("INSERT INTO worker_runs VALUES(?,?,?,?,?,?,?,?)",(run_id,str(tenant_id),str(workspace_id),"running",0,started,None,None))
        try:
            result=self.loop.run(tenant_id,workspace_id,limit)
            finished=self._now().isoformat()
            with self._db() as c:
                c.execute("UPDATE worker_runs SET status=?,event_count=?,finished_at=? WHERE run_id=?",("completed",int(result.get("events",0)),finished,run_id))
                c.execute("UPDATE worker_state SET status=?,last_run_id=?,last_finished_at=?,lease_until=NULL WHERE tenant_id=? AND workspace_id=?",("idle",run_id,finished,str(tenant_id),str(workspace_id)))
            return {"status":"completed","run_id":run_id,"processed":result.get("events",0),"loop":result}
        except Exception as exc:
            finished=self._now().isoformat()
            with self._db() as c:
                c.execute("UPDATE worker_runs SET status=?,finished_at=?,error=? WHERE run_id=?",("failed",finished,str(exc),run_id))
                c.execute("UPDATE worker_state SET status=?,last_run_id=?,last_finished_at=?,lease_until=NULL WHERE tenant_id=? AND workspace_id=?",("failed",run_id,finished,str(tenant_id),str(workspace_id)))
            return {"status":"failed","run_id":run_id,"processed":0,"reason":str(exc)}
    def recover_stale(self,tenant_id,workspace_id):
        now=self._now()
        with self._db() as c:
            row=c.execute("SELECT status,lease_until,last_run_id FROM worker_state WHERE tenant_id=? AND workspace_id=?",(str(tenant_id),str(workspace_id))).fetchone()
            if not row or row["status"] != "running": return {"status":"cleaned","recovered":False}
            lease=row["lease_until"]
            stale=True
            if lease:
                try: stale=datetime.fromisoformat(lease).timestamp() <= now.timestamp()
                except ValueError: stale=True
            if not stale: return {"status":"active","recovered":False,"run_id":row["last_run_id"]}
            run_id=row["last_run_id"]
            if run_id: c.execute("UPDATE worker_runs SET status=?,finished_at=?,error=? WHERE run_id=? AND status=?",("interrupted",now.isoformat(),"lease_expired_recovery",run_id,"running"))
            c.execute("UPDATE worker_state SET status=?,lease_until=NULL,last_finished_at=? WHERE tenant_id=? AND workspace_id=?",("recovered",now.isoformat(),str(tenant_id),str(workspace_id)))
            return {"status":"recovered","recovered":True,"run_id":run_id}
    def reconcile(self,tenant_id=None,workspace_id=None):
        with self._db() as c:
            if tenant_id is not None and workspace_id is not None:
                scopes=[(str(tenant_id),str(workspace_id))]
            else:
                scopes=[(r["tenant_id"],r["workspace_id"]) for r in c.execute("SELECT tenant_id,workspace_id FROM worker_state WHERE status='running'").fetchall()]
        return [self.recover_stale(t,w) for t,w in scopes]
    def state(self,tenant_id,workspace_id):
        with self._db() as c: row=c.execute("SELECT * FROM worker_state WHERE tenant_id=? AND workspace_id=?",(str(tenant_id),str(workspace_id))).fetchone()
        return dict(row) if row else {"tenant_id":str(tenant_id),"workspace_id":str(workspace_id),"status":"idle"}
    def health(self):
        with self._db() as c: runs=c.execute("SELECT COUNT(*) FROM worker_runs").fetchone()[0]
        return {"status":"ok","engine":"agent-event-worker","durable":True,"lease_seconds":self.lease_seconds,"batch_size":self.batch_size,"runs":runs,"safe_shutdown":True}
