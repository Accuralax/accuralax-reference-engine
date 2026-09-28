from __future__ import annotations
import json, os, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class EventAutomation:
    """Tenant-scoped event routing and bounded automation dispatch."""
    def __init__(self, event_bus=None, db_path=None, max_actions=10):
        self.event_bus=event_bus
        self.db_path=db_path or os.path.join("data","event_automation.sqlite3")
        self.max_actions=max(1,min(int(max_actions),25))
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS routes(route_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,event_type TEXT,name TEXT,actions TEXT,active INTEGER,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS dispatches(dispatch_id TEXT PRIMARY KEY,route_id TEXT,tenant_id TEXT,workspace_id TEXT,event_id TEXT,status TEXT,actions TEXT,result TEXT,created_at TEXT)")
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.db_path)
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def define_route(self,t,w,event_type,name,actions):
        t,w=self.scope(t,w)
        if not isinstance(actions,list) or not actions or len(actions)>self.max_actions:return {"allowed":False,"reason":"invalid_action_count"}
        rid="ROUTE-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:c.execute("INSERT INTO routes VALUES(?,?,?,?,?,?,?,?,?)",(rid,t,w,event_type,name,json.dumps(actions),1,now,now))
        return self.get_route(t,w,rid)
    def get_route(self,t,w,rid):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT route_id,event_type,name,actions,active,created_at,updated_at FROM routes WHERE route_id=? AND tenant_id=? AND workspace_id=?",(rid,t,w)).fetchone()
        if not r:return None
        out=dict(zip(("route_id","event_type","name","actions","active","created_at","updated_at"),r)); out["actions"]=json.loads(out["actions"]); return out
    def dispatch(self,t,w,event_id,event_type,payload,handlers=None):
        t,w=self.scope(t,w)
        with self.db() as c: routes=c.execute("SELECT route_id,actions FROM routes WHERE tenant_id=? AND workspace_id=? AND event_type=? AND active=1",(t,w,event_type)).fetchall()
        if not routes:return {"status":"no_route","event_id":event_id,"actions":[]}
        route_results=[]
        all_results=[]
        for rid,raw in routes:
            results=[]
            actions=json.loads(raw); dispatch_id="DISP-"+uuid.uuid4().hex[:12].upper()
            for action in actions:
                try:
                    result=handlers[action.get("action")](action,payload) if handlers and action.get("action") in handlers else {"status":"planned","action":action.get("action")}
                    results.append(result)
                except Exception as exc: results.append({"status":"failed","action":action.get("action"),"error":str(exc)})
            all_results.extend(results)
            route_status="completed" if all(x.get("status") in {"completed","planned"} for x in results) else "failed"
            route_results.append(route_status)
            dispatch_status=route_status
            with self.db() as c:
                c.execute("INSERT INTO dispatches VALUES(?,?,?,?,?,?,?,?,?)",(dispatch_id,rid,t,w,event_id,dispatch_status,json.dumps(actions),json.dumps(results),self.now()))
        return {"status":"completed" if route_results and all(x == "completed" for x in route_results) else "failed","event_id":event_id,"actions":all_results,"route_statuses":route_results}
    def history(self,t,w,limit=100):
        t,w=self.scope(t,w)
        with self.db() as c:rows=c.execute("SELECT dispatch_id,route_id,event_id,status,actions,result,created_at FROM dispatches WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",(t,w,int(limit))).fetchall()
        return [dict(zip(("dispatch_id","route_id","event_id","status","actions","result","created_at"),r)) for r in rows]
    def health(self):
        with self.db() as c:a=c.execute("SELECT COUNT(*) FROM routes").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM dispatches").fetchone()[0]
        return {"status":"ok","routes":a,"dispatches":b,"tenant_scoped":True,"bounded_actions":self.max_actions}
