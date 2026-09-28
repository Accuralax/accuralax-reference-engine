from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class DataGovernanceQuality:
    """Tenant-scoped data catalog, quality evidence and lineage registry."""
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','data_governance.sqlite3');os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS datasets(dataset_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,owner TEXT,class TEXT,status TEXT,created_at TEXT,updated_at TEXT,UNIQUE(tenant_id,workspace_id,name))')
            c.execute('CREATE TABLE IF NOT EXISTS quality_checks(check_id TEXT PRIMARY KEY,dataset_id TEXT,tenant_id TEXT,workspace_id TEXT,check_type TEXT,status TEXT,score REAL,details_json TEXT,created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS lineage(lineage_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,source_dataset TEXT,target_dataset TEXT,transformation TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def register(self,t,w,name,owner='system',classification='internal',status='active'):
        if not t or not w or not name:raise ValueError('tenant_workspace_name_required')
        now=datetime.now(timezone.utc).isoformat();did='DS-'+uuid.uuid4().hex[:12].upper()
        with self.db() as c:c.execute('INSERT OR REPLACE INTO datasets VALUES(?,?,?,?,?,?,?,?,?)',(did,str(t),str(w),str(name),str(owner),str(classification),str(status),now,now))
        return self.get(t,w,name)
    def get(self,t,w,name):
        with self.db() as c:r=c.execute('SELECT * FROM datasets WHERE tenant_id=? AND workspace_id=? AND name=?',(str(t),str(w),str(name))).fetchone()
        return dict(r) if r else None
    def check(self,t,w,dataset,check_type,status,score,details=None):
        d=self.get(t,w,dataset)
        if not d:raise ValueError('dataset_not_found')
        cid='DQ-'+uuid.uuid4().hex[:12].upper();now=datetime.now(timezone.utc).isoformat()
        with self.db() as c:c.execute('INSERT INTO quality_checks VALUES(?,?,?,?,?,?,?,?,?)',(cid,d['dataset_id'],str(t),str(w),str(check_type),str(status),float(score),json.dumps(details or {},sort_keys=True),now))
        return {'check_id':cid,'dataset':dataset,'check_type':check_type,'status':status,'score':float(score),'details':details or {}}
    def add_lineage(self,t,w,source,target,transformation=''):
        lid='LIN-'+uuid.uuid4().hex[:12].upper();now=datetime.now(timezone.utc).isoformat()
        with self.db() as c:c.execute('INSERT INTO lineage VALUES(?,?,?,?,?,?,?)',(lid,str(t),str(w),str(source),str(target),str(transformation),now))
        return {'lineage_id':lid,'source_dataset':source,'target_dataset':target,'transformation':transformation}
    def snapshot(self,t,w):
        with self.db() as c:
            ds=c.execute('SELECT * FROM datasets WHERE tenant_id=? AND workspace_id=?',(str(t),str(w))).fetchall();qs=c.execute('SELECT * FROM quality_checks WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC',(str(t),str(w))).fetchall();ln=c.execute('SELECT * FROM lineage WHERE tenant_id=? AND workspace_id=?',(str(t),str(w))).fetchall()
        return {'datasets':[dict(x) for x in ds],'quality_checks':[dict(x) for x in qs],'lineage':[dict(x) for x in ln]}
    def health(self):
        with self.db() as c:d=c.execute('SELECT COUNT(*) FROM datasets').fetchone()[0];q=c.execute('SELECT COUNT(*) FROM quality_checks').fetchone()[0];l=c.execute('SELECT COUNT(*) FROM lineage').fetchone()[0]
        return {'status':'ok','durable':True,'tenant_workspace_scoped':True,'datasets':d,'quality_checks':q,'lineage_records':l,'governed':True}
