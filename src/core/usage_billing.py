from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class UsageBilling:
    """Tenant-scoped usage ledger and deterministic plan metering."""
    PLANS={'free':{'included_units':100,'unit_price':0.0},'starter':{'included_units':5000,'unit_price':0.02},'business':{'included_units':25000,'unit_price':0.015},'enterprise':{'included_units':100000,'unit_price':0.01}}
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','usage_billing.sqlite3');os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS accounts(tenant_id TEXT,workspace_id TEXT,plan TEXT,status TEXT,created_at TEXT,PRIMARY KEY(tenant_id,workspace_id))')
            c.execute('CREATE TABLE IF NOT EXISTS usage(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,metric TEXT,units REAL,reference_id TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def account(self,t,w,plan='free'):
        plan=str(plan).lower()
        if plan not in self.PLANS:raise ValueError('invalid_plan')
        with self.db() as c:c.execute('INSERT OR REPLACE INTO accounts VALUES(?,?,?,?,?)',(str(t),str(w),plan,'active',datetime.now(timezone.utc).isoformat()))
        return {'tenant_id':str(t),'workspace_id':str(w),'plan':plan,'status':'active'}
    def record(self,t,w,metric,units,reference_id=None):
        with self.db() as c:a=c.execute('SELECT plan FROM accounts WHERE tenant_id=? AND workspace_id=?',(str(t),str(w))).fetchone()
        if not a:self.account(t,w)
        item={'id':'USE-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'metric':str(metric),'units':float(units),'reference_id':reference_id,'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO usage VALUES(?,?,?,?,?,?,?)',(item['id'],item['tenant_id'],item['workspace_id'],item['metric'],item['units'],item['reference_id'],item['created_at']))
        return item
    def invoice_preview(self,t,w):
        with self.db() as c:
            a=c.execute('SELECT * FROM accounts WHERE tenant_id=? AND workspace_id=?',(str(t),str(w))).fetchone();u=c.execute('SELECT COALESCE(SUM(units),0) FROM usage WHERE tenant_id=? AND workspace_id=?',(str(t),str(w))).fetchone()[0]
        plan=a['plan'] if a else 'free';cfg=self.PLANS[plan];over=max(0,float(u)-cfg['included_units']);return {'tenant_id':str(t),'workspace_id':str(w),'plan':plan,'used_units':float(u),'included_units':cfg['included_units'],'overage_units':over,'estimated_charge':round(over*cfg['unit_price'],2),'currency':'ZAR'}
    def health(self):
        with self.db() as c:a=c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0];u=c.execute('SELECT COUNT(*) FROM usage').fetchone()[0]
        return {'status':'ok','durable':True,'tenant_workspace_scoped':True,'plans':sorted(self.PLANS),'accounts':a,'usage_records':u,'currency':'ZAR'}
