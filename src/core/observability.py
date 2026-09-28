from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class Observability:
    """Durable metrics, structured logs and traces with tenant/workspace scope."""
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','observability.sqlite3');os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS metrics(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,value REAL,labels_json TEXT,created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS logs(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,level TEXT,message TEXT,trace_id TEXT,correlation_id TEXT,metadata_json TEXT,created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS traces(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,trace_id TEXT,span TEXT,status TEXT,duration_ms REAL,metadata_json TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path, timeout=15.0);c.execute('PRAGMA busy_timeout=15000');c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def metric(self,t,w,name,value,labels=None):
        item={'id':'MET-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'name':str(name),'value':float(value),'labels':labels or {},'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO metrics VALUES(?,?,?,?,?,?,?)',(item['id'],item['tenant_id'],item['workspace_id'],item['name'],item['value'],json.dumps(item['labels'],sort_keys=True),item['created_at']))
        return item
    def log(self,t,w,level,message,trace_id=None,correlation_id=None,metadata=None):
        blocked={'password','token','secret','api_key','authorization'};safe={str(k):v for k,v in (metadata or {}).items() if str(k).lower() not in blocked}
        item={'id':'LOG-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'level':str(level).upper(),'message':str(message),'trace_id':trace_id,'correlation_id':correlation_id,'metadata':safe,'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO logs VALUES(?,?,?,?,?,?,?,?,?)',(item['id'],item['tenant_id'],item['workspace_id'],item['level'],item['message'],trace_id,correlation_id,json.dumps(safe,sort_keys=True),item['created_at']))
        return item
    def trace(self,t,w,trace_id,span,status='completed',duration_ms=0,metadata=None):
        item={'id':'SPAN-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'trace_id':str(trace_id),'span':str(span),'status':str(status),'duration_ms':float(duration_ms),'metadata':metadata or {},'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO traces VALUES(?,?,?,?,?,?,?,?,?)',(item['id'],item['tenant_id'],item['workspace_id'],item['trace_id'],item['span'],item['status'],item['duration_ms'],json.dumps(item['metadata'],sort_keys=True),item['created_at']))
        return item
    def snapshot(self,t,w):
        with self.db() as c:
            m=c.execute('SELECT * FROM metrics WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT 100',(str(t),str(w))).fetchall();l=c.execute('SELECT * FROM logs WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT 100',(str(t),str(w))).fetchall();tr=c.execute('SELECT * FROM traces WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT 100',(str(t),str(w))).fetchall()
        return {'metrics':[dict(x) for x in m],'logs':[dict(x) for x in l],'traces':[dict(x) for x in tr]}
    def health(self):
        with self.db() as c:m=c.execute('SELECT COUNT(*) FROM metrics').fetchone()[0];l=c.execute('SELECT COUNT(*) FROM logs').fetchone()[0];tr=c.execute('SELECT COUNT(*) FROM traces').fetchone()[0]
        return {'status':'ok','durable':True,'tenant_workspace_scoped':True,'structured_logging':True,'tracing':True,'metrics':m,'logs':l,'traces':tr}
