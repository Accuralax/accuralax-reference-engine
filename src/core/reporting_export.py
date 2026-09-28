from __future__ import annotations
import csv, io, json, os, sqlite3, uuid
from datetime import datetime, timezone

class ReportingExport:
    """Tenant-scoped report definitions, generated reports and controlled exports."""
    FORMATS={"json","csv"}
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","reporting_export.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS reports(report_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,report_type TEXT,definition TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS generated(report_run_id TEXT PRIMARY KEY,report_id TEXT,tenant_id TEXT,workspace_id TEXT,status TEXT,format TEXT,payload TEXT,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def define(self,t,w,name,report_type="operational",definition=None):
        t,w=self.scope(t,w); rid="RPT-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            c.execute("INSERT INTO reports VALUES(?,?,?,?,?,?,?,?)",(rid,t,w,name,report_type,json.dumps(definition or {}),now,now))
        return self.get(t,w,rid)
    def get(self,t,w,report_id):
        t,w=self.scope(t,w)
        with self.db() as c: row=c.execute("SELECT report_id,name,report_type,definition,created_at,updated_at FROM reports WHERE report_id=? AND tenant_id=? AND workspace_id=?",(report_id,t,w)).fetchone()
        if not row:return None
        keys=("report_id","name","report_type","definition","created_at","updated_at"); out=dict(zip(keys,row)); out["definition"]=json.loads(out["definition"] or "{}"); return out
    def generate(self,t,w,report_id,data,fmt="json"):
        t,w=self.scope(t,w)
        if fmt not in self.FORMATS:return {"allowed":False,"reason":"unsupported_format"}
        if not self.get(t,w,report_id):return {"allowed":False,"reason":"report_not_found"}
        payload=json.dumps(data,ensure_ascii=False)
        if fmt=="csv":
            if isinstance(data,list) and data and isinstance(data[0],dict):
                s=io.StringIO(); writer=csv.DictWriter(s,fieldnames=list(data[0].keys())); writer.writeheader(); writer.writerows(data); payload=s.getvalue()
            else:return {"allowed":False,"reason":"csv_requires_list_of_objects"}
        run="RUN-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:c.execute("INSERT INTO generated VALUES(?,?,?,?,?,?,?,?)",(run,report_id,t,w,"completed",fmt,payload,now))
        return {"report_run_id":run,"report_id":report_id,"status":"completed","format":fmt,"payload":payload}
    def history(self,t,w,report_id=None):
        t,w=self.scope(t,w)
        q="SELECT report_run_id,report_id,status,format,created_at FROM generated WHERE tenant_id=? AND workspace_id=?"; args=[t,w]
        if report_id:q+=" AND report_id=?"; args.append(report_id)
        q+=" ORDER BY created_at DESC"
        with self.db() as c: rows=c.execute(q,args).fetchall()
        return [dict(zip(("report_run_id","report_id","status","format","created_at"),r)) for r in rows]
    def health(self):
        with self.db() as c: a=c.execute("SELECT COUNT(*) FROM reports").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM generated").fetchone()[0]
        return {"status":"ok","reports":a,"generated_runs":b,"tenant_scoped":True,"formats":sorted(self.FORMATS)}
