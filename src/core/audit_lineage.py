from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class AuditLineage:
    """Durable, tenant-scoped audit trail for cross-system actions and decisions."""
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','audit_lineage.sqlite3'); os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:c.execute('CREATE TABLE IF NOT EXISTS audit_events(audit_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,actor_id TEXT NOT NULL,trace_id TEXT,correlation_id TEXT,source TEXT NOT NULL,event_type TEXT NOT NULL,entity_type TEXT,entity_id TEXT,reference_id TEXT,status TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL)')
    def db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def record(self,tenant_id,workspace_id,actor_id,event_type,source='system',status='completed',entity_type=None,entity_id=None,reference_id=None,trace_id=None,correlation_id=None,metadata=None):
        if not tenant_id or not workspace_id or not event_type:raise ValueError('tenant_workspace_event_required')
        blocked={'password','token','secret','api_key','access_token','authorization'}
        safe={str(k):v for k,v in (metadata or {}).items() if str(k).lower() not in blocked}
        item={'audit_id':'AUD-'+uuid.uuid4().hex[:16].upper(),'tenant_id':str(tenant_id),'workspace_id':str(workspace_id),'actor_id':str(actor_id or 'system'),'trace_id':trace_id,'correlation_id':correlation_id,'source':str(source),'event_type':str(event_type),'entity_type':entity_type,'entity_id':entity_id,'reference_id':reference_id,'status':str(status),'metadata':safe,'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(item['audit_id'],item['tenant_id'],item['workspace_id'],item['actor_id'],item['trace_id'],item['correlation_id'],item['source'],item['event_type'],item['entity_type'],item['entity_id'],item['reference_id'],item['status'],json.dumps(safe,sort_keys=True),item['created_at']))
        return item
    def history(self,tenant_id,workspace_id,limit=100,event_type=None):
        q='SELECT * FROM audit_events WHERE tenant_id=? AND workspace_id=?';args=[str(tenant_id),str(workspace_id)]
        if event_type:q+=' AND event_type=?';args.append(str(event_type))
        q+=' ORDER BY created_at DESC LIMIT ?';args.append(max(1,min(int(limit),500)))
        with self.db() as c:rows=c.execute(q,args).fetchall()
        out=[]
        for r in rows:
            x=dict(r);x['metadata']=json.loads(x.pop('metadata_json'));out.append(x)
        return out
    def health(self):
        with self.db() as c:n=c.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
        return {'status':'ok','durable':True,'tenant_workspace_scoped':True,'credential_filtered':True,'events':n}
