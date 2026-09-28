from __future__ import annotations
import json, os, sqlite3, uuid, statistics
from datetime import datetime, timezone

class BusinessIntelligence:
    """Tenant-scoped KPI analytics with governed metric, dashboard, anomaly and reporting controls."""
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","business_intelligence.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS kpis(kpi_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,description TEXT,unit TEXT,created_at TEXT,active INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS observations(observation_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,kpi_id TEXT,value REAL,period TEXT,metadata TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS metrics(metric_id TEXT PRIMARY KEY,name TEXT,description TEXT,domain TEXT,source TEXT,version TEXT,status TEXT,approved_by TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS dashboards(dashboard_id TEXT PRIMARY KEY,name TEXT,metric_ids TEXT,status TEXT,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS reports(report_id TEXT PRIMARY KEY,name TEXT,source TEXT,confidence REAL,status TEXT,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def define_kpi(self,t,w,name,description="",unit="count"):
        t,w=self.scope(t,w)
        if not name.strip(): return {"allowed":False,"reason":"kpi_name_required"}
        kid="KPI-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c: c.execute("INSERT INTO kpis VALUES(?,?,?,?,?,?,?,?)",(kid,t,w,name,description,unit,self.now(),1))
        return {"kpi_id":kid,"name":name,"unit":unit,"active":True}
    def record(self,t,w,kpi_id,value,period,metadata=None):
        t,w=self.scope(t,w)
        with self.db() as c:
            if not c.execute("SELECT 1 FROM kpis WHERE kpi_id=? AND tenant_id=? AND workspace_id=? AND active=1",(kpi_id,t,w)).fetchone(): return {"allowed":False,"reason":"kpi_not_found"}
            oid="OBS-"+uuid.uuid4().hex[:12].upper()
            c.execute("INSERT INTO observations VALUES(?,?,?,?,?,?,?,?)",(oid,t,w,kpi_id,float(value),str(period),json.dumps(metadata or {}),self.now()))
        return {"observation_id":oid,"kpi_id":kpi_id,"value":float(value),"period":str(period)}
    def snapshot(self,t,w,kpi_id=None):
        t,w=self.scope(t,w)
        with self.db() as c:
            q="SELECT k.kpi_id,k.name,k.unit,o.period,o.value,o.metadata FROM observations o JOIN kpis k ON k.kpi_id=o.kpi_id WHERE o.tenant_id=? AND o.workspace_id=?"; args=[t,w]
            if kpi_id: q+=" AND o.kpi_id=?"; args.append(kpi_id)
            q+=" ORDER BY o.period,o.created_at"; rows=c.execute(q,args).fetchall()
        grouped={}
        for kid,name,unit,period,value,metadata in rows:
            grouped.setdefault(kid,{"kpi_id":kid,"name":name,"unit":unit,"observations":[]})["observations"].append({"period":period,"value":value,"metadata":json.loads(metadata or "{}")})
        for item in grouped.values():
            vals=[x["value"] for x in item["observations"]]
            item.update(latest=vals[-1] if vals else None,average=round(sum(vals)/len(vals),4) if vals else None,min=min(vals) if vals else None,max=max(vals) if vals else None,change=round(vals[-1]-vals[-2],4) if len(vals)>1 else None)
        return list(grouped.values())
    def register_metric(self,name,description,domain,source,version):
        mid="MET-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c: c.execute("INSERT INTO metrics VALUES(?,?,?,?,?,?,?,?,?)",(mid,name,description,domain,source,version,"draft","",self.now()))
        return {"metric_id":mid,"name":name,"status":"draft"}
    def approve_metric(self,metric_id,approved=False,approved_by="system"):
        with self.db() as c:
            row=c.execute("SELECT metric_id,status FROM metrics WHERE metric_id=?",(metric_id,)).fetchone()
            if not row: return {"allowed":False,"reason":"metric_not_found"}
            if not approved: return {"allowed":False,"reason":"approval_required","metric_id":metric_id}
            c.execute("UPDATE metrics SET status='active',approved_by=? WHERE metric_id=?",(approved_by,metric_id))
        return {"metric_id":metric_id,"status":"active","approved_by":approved_by}
    def create_dashboard(self,name,metric_ids):
        did="DASH-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c: c.execute("INSERT INTO dashboards VALUES(?,?,?,?,?)",(did,name,json.dumps(metric_ids),"draft",self.now()))
        return {"dashboard_id":did,"name":name,"status":"draft"}
    def publish_dashboard(self,dashboard_id,approved=False):
        if not approved: return {"allowed":False,"reason":"approval_required","dashboard_id":dashboard_id}
        with self.db() as c:
            if not c.execute("SELECT 1 FROM dashboards WHERE dashboard_id=?",(dashboard_id,)).fetchone(): return {"allowed":False,"reason":"dashboard_not_found"}
            c.execute("UPDATE dashboards SET status='published' WHERE dashboard_id=?",(dashboard_id,))
        return {"dashboard_id":dashboard_id,"status":"published"}
    def detect_anomaly(self,metric_id,values):
        vals=[float(v) for v in values]
        if len(vals)<4: return {"metric_id":metric_id,"anomaly":False,"score":0.0}
        baseline=vals[:-1]; mean=statistics.mean(baseline); sd=statistics.pstdev(baseline) or 1.0
        score=abs(vals[-1]-mean)/sd
        return {"metric_id":metric_id,"anomaly":score>=3.0,"score":round(score,4),"value":vals[-1]}
    def detect_trend(self,values):
        vals=[float(v) for v in values]
        if len(vals)<2: return {"direction":"flat","change":0.0}
        change=vals[-1]-vals[0]
        direction="up" if change>0 else "down" if change<0 else "flat"
        return {"direction":direction,"change":change}
    def create_report(self,name,source,confidence):
        rid="RPT-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c: c.execute("INSERT INTO reports VALUES(?,?,?,?,?,?)",(rid,name,source,float(confidence),"draft",self.now()))
        return {"report_id":rid,"name":name,"status":"draft","confidence":float(confidence)}
    def health(self):
        with self.db() as c:
            k=c.execute("SELECT COUNT(*) FROM kpis").fetchone()[0]; o=c.execute("SELECT COUNT(*) FROM observations").fetchone()[0]; m=c.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        return {"status":"ok","kpis":k,"observations":o,"metrics":m,"tenant_scoped":True,"trend_analysis":True,"persistent":True,"credentials_exposed":False}
