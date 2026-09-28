from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class RecoveryManager:
    """Durable recovery ledger for checkpoints, backups and restore operations."""
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','recovery.sqlite3');os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS checkpoints(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,label TEXT,state_json TEXT,created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS recovery_runs(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,checkpoint_id TEXT,action TEXT,status TEXT,reason TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def checkpoint(self,t,w,label,state=None):
        item={'id':'CHK-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'label':str(label),'state':state or {},'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO checkpoints VALUES(?,?,?,?,?,?)',(item['id'],item['tenant_id'],item['workspace_id'],item['label'],json.dumps(item['state'],sort_keys=True),item['created_at']))
        return item
    def recover(self,t,w,checkpoint_id,action='restore',approved=False):
        with self.db() as c:r=c.execute('SELECT * FROM checkpoints WHERE tenant_id=? AND workspace_id=? AND id=?',(str(t),str(w),checkpoint_id)).fetchone()
        if not r:return {'allowed':False,'reason':'checkpoint_not_found'}
        if not approved:return {'allowed':False,'reason':'human_approval_required','checkpoint_id':checkpoint_id}
        rid='REC-'+uuid.uuid4().hex[:12].upper();now=datetime.now(timezone.utc).isoformat()
        with self.db() as c:c.execute('INSERT INTO recovery_runs VALUES(?,?,?,?,?,?,?,?)',(rid,str(t),str(w),checkpoint_id,str(action),'completed','approved',now))
        return {'allowed':True,'recovery_id':rid,'checkpoint_id':checkpoint_id,'action':action,'status':'completed'}
    def history(self,t,w,limit=100):
        with self.db() as c:rows=c.execute('SELECT * FROM recovery_runs WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?',(str(t),str(w),max(1,min(int(limit),500)))).fetchall()
        return [dict(x) for x in rows]
    def health(self):
        with self.db() as c:c1=c.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0];c2=c.execute('SELECT COUNT(*) FROM recovery_runs').fetchone()[0]
        return {'status':'ok','durable':True,'tenant_workspace_scoped':True,'approval_required_for_restore':True,'checkpoints':c1,'recovery_runs':c2}
