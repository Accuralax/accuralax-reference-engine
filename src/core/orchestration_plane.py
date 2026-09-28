from __future__ import annotations
import json, os, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class OrchestrationPlane:
    """Durable coordinator for planner, executor and integration commands."""
    def __init__(self, planner=None, executor=None, integration=None, event_bus=None, db_path=None, max_steps=10):
        self.planner=planner; self.executor=executor; self.integration=integration; self.events=event_bus
        self.db_path=db_path or os.path.join('data','orchestration_plane.sqlite3'); self.max_steps=max(1,min(int(max_steps),20))
        os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self._db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,run_type TEXT NOT NULL,status TEXT NOT NULL,requested_by TEXT NOT NULL,correlation_id TEXT NOT NULL,trace_id TEXT NOT NULL,input_json TEXT NOT NULL,result_json TEXT,reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(tenant_id,workspace_id,correlation_id))')
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path, timeout=15.0); c.execute("PRAGMA busy_timeout=15000"); c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()
    def create(self, tenant_id, workspace_id, run_type, payload=None, requested_by='system', correlation_id=None, trace_id=None):
        if not tenant_id or not workspace_id: raise ValueError('tenant_id_and_workspace_id_required')
        correlation_id=correlation_id or 'CORR-'+uuid.uuid4().hex[:12].upper(); trace_id=trace_id or 'TRACE-'+uuid.uuid4().hex[:12].upper()
        with self._db() as c:
            old=c.execute('SELECT * FROM runs WHERE tenant_id=? AND workspace_id=? AND correlation_id=?',(str(tenant_id),str(workspace_id),correlation_id)).fetchone()
            if old:return self._row(old)
        rid='RUN-'+uuid.uuid4().hex[:16].upper(); now=datetime.now(timezone.utc).isoformat()
        with self._db() as c:c.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,str(tenant_id),str(workspace_id),str(run_type),'queued',str(requested_by),correlation_id,trace_id,json.dumps(payload or {}),None,None,now,now))
        return self.get(tenant_id,workspace_id,rid)
    def execute(self, tenant_id, workspace_id, run_id):
        run=self.get(tenant_id,workspace_id,run_id)
        if run['status'] in ('completed','cancelled'): return run
        self._update(run_id,tenant_id,workspace_id,status='running')
        try: result=self._dispatch(run,run['input'])
        except Exception as exc: result={'status':'failed','reason':str(exc)}
        self._update(run_id,tenant_id,workspace_id,status=result.get('status','completed'),result=result,reason=result.get('reason'))
        return self.get(tenant_id,workspace_id,run_id)
    def _dispatch(self, run, payload):
        tenant_id,workspace_id=run['tenant_id'],run['workspace_id']; kind=run['run_type']
        if kind=='plan.create':
            if not self.planner: raise ValueError('planner_unavailable')
            return self.planner.plan(tenant_id,workspace_id,payload['client_id'],payload.get('lead'),payload.get('opportunity'),payload.get('consent_granted',False),payload.get('open_tasks',0),payload.get('trigger','orchestration'),payload.get('agent_id','default'))
        if kind=='plan.execute':
            if not self.executor: raise ValueError('plan_executor_unavailable')
            return self.executor.execute(tenant_id,workspace_id,payload['plan_id'],approver_id=payload.get('approver_id'),owner_id=payload.get('owner_id'),task=payload.get('task'),opportunity=payload.get('opportunity'),changed_by=run['requested_by'])
        if kind=='integration.dispatch':
            if not self.integration: raise ValueError('integration_layer_unavailable')
            return self.integration.dispatch(tenant_id,workspace_id,payload['connector'],payload['action'],payload.get('payload',{}),run['requested_by'],payload.get('idempotency_key'),run['trace_id'],run['correlation_id'],bool(payload.get('approval_required',False)),payload.get('approval_id'))
        if kind=='pipeline':
            results=[]
            for step in payload.get('steps',[])[:self.max_steps]:
                result=self.integration.dispatch(tenant_id,workspace_id,step['connector'],step['action'],step.get('payload',{}),run['requested_by'],step.get('idempotency_key'),run['trace_id'],run['correlation_id'],bool(step.get('approval_required',False)),step.get('approval_id'))
                results.append(result)
                if result.get('status') in ('failed','dead_letter','blocked'): return {'status':'awaiting_approval' if result.get('status')=='blocked' else 'failed','steps':results}
            return {'status':'completed','steps':results}
        raise ValueError('unsupported_run_type')
    def _update(self,rid,t,w,**changes):
        sets=[]; vals=[]
        for key,value in changes.items():
            column={'result':'result_json'}.get(key,key); sets.append(column+'=?'); vals.append(json.dumps(value,sort_keys=True) if key=='result' else value)
        sets.append('updated_at=?'); vals.append(datetime.now(timezone.utc).isoformat()); vals.extend([rid,str(t),str(w)])
        with self._db() as c:c.execute('UPDATE runs SET '+','.join(sets)+' WHERE run_id=? AND tenant_id=? AND workspace_id=?',vals)
    @staticmethod
    def _row(row):
        item=dict(row); item['input']=json.loads(item.pop('input_json')); raw=item.pop('result_json'); item['result']=json.loads(raw) if raw else None; return item
    def get(self,t,w,rid):
        with self._db() as c: row=c.execute('SELECT * FROM runs WHERE tenant_id=? AND workspace_id=? AND run_id=?',(str(t),str(w),rid)).fetchone()
        if not row: raise ValueError('run_not_found')
        return self._row(row)
    def history(self,t,w,limit=100):
        with self._db() as c: rows=c.execute('SELECT * FROM runs WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?',(str(t),str(w),max(1,min(int(limit),500)))).fetchall()
        return [self._row(row) for row in rows]
    def health(self):
        with self._db() as c: count=c.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
        return {'status':'ok','engine':'orchestration-plane','durable':True,'tenant_workspace_scoped':True,'bounded':True,'max_steps':self.max_steps,'runs':count,'approval_aware':True,'integration_aware':True}
