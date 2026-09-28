import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone


class AgentScheduler:
    """Controlled background heartbeat for registered tenant/workspace workers."""
    def __init__(self, worker, db_path=None, interval_seconds=30):
        self.worker=worker
        self.db_path=db_path or os.path.join("data","agent_scheduler.sqlite3")
        self.interval=max(1,min(int(interval_seconds),3600)); self._thread=None; self._stop=threading.Event(); self._lock=threading.Lock()
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS scheduler_scopes(tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,enabled INTEGER NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(tenant_id,workspace_id))")
            c.execute("CREATE TABLE IF NOT EXISTS scheduler_runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT,tenant_id TEXT,workspace_id TEXT,status TEXT,started_at TEXT,finished_at TEXT,error TEXT)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def register(self,tenant_id,workspace_id,enabled=True):
        now=datetime.now(timezone.utc).isoformat()
        with self._db() as c: c.execute("INSERT INTO scheduler_scopes VALUES(?,?,?,?) ON CONFLICT(tenant_id,workspace_id) DO UPDATE SET enabled=excluded.enabled",(str(tenant_id),str(workspace_id),int(bool(enabled)),now))
        return {"tenant_id":str(tenant_id),"workspace_id":str(workspace_id),"enabled":bool(enabled)}
    def scopes(self):
        with self._db() as c: rows=c.execute("SELECT tenant_id,workspace_id,enabled,created_at FROM scheduler_scopes ORDER BY created_at").fetchall()
        return [dict(r) | {"enabled":bool(r["enabled"])} for r in rows]
    def _tick(self):
        for scope in self.scopes():
            if not scope["enabled"]: continue
            t,w=scope["tenant_id"],scope["workspace_id"]
            started=datetime.now(timezone.utc).isoformat()
            try:
                result=self.worker.run_once(t,w)
                status=result.get("status","completed"); error=result.get("reason")
            except Exception as exc:
                status="failed"; error=str(exc)
            finished=datetime.now(timezone.utc).isoformat()
            with self._db() as c: c.execute("INSERT INTO scheduler_runs(tenant_id,workspace_id,status,started_at,finished_at,error) VALUES(?,?,?,?,?,?)",(t,w,status,started,finished,error))
    def _loop(self):
        while not self._stop.is_set():
            self._tick(); self._stop.wait(self.interval)
    def start(self):
        health=getattr(self.worker,"health",None)
        if callable(health):
            state=health()
            if state.get("status") in {"degraded","failed"}:
                return {"status":"blocked","reason":"worker_not_ready","worker_health":state}
        reconcile=getattr(self.worker,"reconcile",None)
        if callable(reconcile): reconcile()
        with self._lock:
            if self._thread and self._thread.is_alive(): return {"status":"already_running"}
            self._stop.clear(); self._thread=threading.Thread(target=self._loop,name="agent-scheduler",daemon=True); self._thread.start()
        return {"status":"started","interval_seconds":self.interval}
    def stop(self):
        self._stop.set(); thread=self._thread
        if thread and thread is not threading.current_thread(): thread.join(timeout=min(self.interval,5))
        return {"status":"stopped"}
    def status(self):
        running=bool(self._thread and self._thread.is_alive())
        with self._db() as c: count=c.execute("SELECT COUNT(*) FROM scheduler_runs").fetchone()[0]
        return {"status":"running" if running else "stopped","interval_seconds":self.interval,"scope_count":len(self.scopes()),"runs":count}
    def health(self):
        return {"status":"ok","engine":"agent-scheduler","daemon":True,"controlled_scopes":True,"worker_health":self.worker.health()}
