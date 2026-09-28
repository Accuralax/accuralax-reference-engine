from __future__ import annotations
import json, os, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus
from .human_approval import HumanApprovalGateway

class EnterpriseIntegrationLayer:
    """Durable, tenant-scoped integration plane for internal and external adapters."""
    STATUSES=("queued","running","completed","failed","dead_letter","blocked")
    def __init__(self,event_bus=None,approval_gateway=None,db_path=None,max_attempts=3,audit=None,observability=None):
        self.events=event_bus or EventBus()
        self.approvals=approval_gateway or HumanApprovalGateway()
        self.db_path=db_path or os.path.join("data","enterprise_integrations.sqlite3")
        self.max_attempts=max(1,min(int(max_attempts),10))
        self.connectors={}
        self.audit=audit
        self.observability=observability
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS integration_jobs(
                job_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,
                connector TEXT NOT NULL,action TEXT NOT NULL,status TEXT NOT NULL,
                payload_json TEXT NOT NULL,attempts INTEGER NOT NULL,trace_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,idempotency_key TEXT,approval_id TEXT,
                result_json TEXT,reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,workspace_id,idempotency_key))""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_integration_scope ON integration_jobs(tenant_id,workspace_id,created_at)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path, timeout=15.0); c.execute("PRAGMA busy_timeout=15000"); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    @staticmethod
    def _scope(t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def register_connector(self,name,handler=None,capabilities=None,health=None):
        key=str(name).strip()
        if not key: raise ValueError("connector_name_required")
        self.connectors[key]={"name":key,"handler":handler,"capabilities":list(capabilities or []),"health":health}
        return {k:v for k,v in self.connectors[key].items() if k!="handler"}
    def connectors_list(self):
        return [{k:v for k,v in x.items() if k!="handler"} for x in self.connectors.values()]
    def _telemetry(self,job,actor_id,event_type,status,attempt=None,metadata=None):
        safe=dict(metadata or {})
        safe.update({"connector":job["connector"],"action":job["action"],"job_id":job["job_id"]})
        if attempt is not None: safe["attempt"]=attempt
        if self.audit:
            try:self.audit.record(job["tenant_id"],job["workspace_id"],actor_id,event_type,source="integration",status=status,entity_type="integration_job",entity_id=job["job_id"],reference_id=job["job_id"],trace_id=job["trace_id"],correlation_id=job["correlation_id"],metadata=safe)
            except Exception: pass
        if self.observability:
            try:self.observability.log(job["tenant_id"],job["workspace_id"],"INFO",event_type,trace_id=job["trace_id"],correlation_id=job["correlation_id"],metadata=dict(safe,status=status))
            except Exception: pass
    def health(self):
        return {"status":"ok","engine":"enterprise-integration-layer","connectors":len(self.connectors),
                "durable_jobs":True,"tenant_isolation":True,"workspace_isolation":True,
                "idempotency":True,"retry_policy":True,"dead_letter":True,"approval_gating":True,
                "traceability":True}
    def dispatch(self,tenant_id,workspace_id,connector,action,payload=None,actor_id="system",
                 idempotency_key=None,trace_id=None,correlation_id=None,approval_required=False,approval_id=None):
        tenant_id,workspace_id=self._scope(tenant_id,workspace_id)
        connector=str(connector); action=str(action)
        if connector not in self.connectors: raise ValueError("connector_not_registered")
        now=self._now(); job_id="INT-"+uuid.uuid4().hex[:16].upper()
        trace_id=trace_id or "TRACE-"+uuid.uuid4().hex[:12].upper()
        correlation_id=correlation_id or "CORR-"+uuid.uuid4().hex[:12].upper()
        status="queued"
        if approval_required:
            if not approval_id: raise ValueError("approval_required")
            approval=self.approvals.get(tenant_id,workspace_id,approval_id)
            if approval["status"]!="approved": status="blocked"
        with self._db() as c:
            if idempotency_key:
                old=c.execute("SELECT * FROM integration_jobs WHERE tenant_id=? AND workspace_id=? AND idempotency_key=?",
                              (tenant_id,workspace_id,str(idempotency_key))).fetchone()
                if old: return self._row(old)
            c.execute("INSERT INTO integration_jobs(job_id,tenant_id,workspace_id,connector,action,status,payload_json,attempts,trace_id,correlation_id,idempotency_key,approval_id,result_json,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (job_id,tenant_id,workspace_id,connector,action,status,json.dumps(payload or {},sort_keys=True),0,trace_id,correlation_id,idempotency_key,approval_id,None,
                       "approval_pending" if status=="blocked" else None,now,now))
        self.events.publish("integration.job.queued",tenant_id,workspace_id,actor_id,"integration_job",job_id,job_id,
                            {"connector":connector,"action":action,"status":status,"correlation_id":correlation_id},trace_id=trace_id,
                            idempotency_key=f"queued:{job_id}")
        queued_job=self.get(tenant_id,workspace_id,job_id)
        self._telemetry(queued_job,actor_id,"integration.job.queued",status,metadata={"approval_id":approval_id})
        if status=="blocked": return self.get(tenant_id,workspace_id,job_id)
        return self.run(tenant_id,workspace_id,job_id,actor_id)
    def run(self,tenant_id,workspace_id,job_id,actor_id="system"):
        job=self.get(tenant_id,workspace_id,job_id)
        if job["status"]=="blocked":
            if job["approval_id"]:
                approval=self.approvals.get(tenant_id,workspace_id,job["approval_id"])
                if approval["status"]!="approved": return job
            self._update(job_id,tenant_id,workspace_id,status="queued",reason=None)
            job=self.get(tenant_id,workspace_id,job_id)
        connector=self.connectors.get(job["connector"])
        if not connector or not connector.get("handler"):
            self._update(job_id,tenant_id,workspace_id,status="dead_letter",reason="connector_handler_unavailable",attempts=job["attempts"]+1)
            return self.get(tenant_id,workspace_id,job_id)
        attempt=job["attempts"]+1
        self._update(job_id,tenant_id,workspace_id,status="running",attempts=attempt,reason=None)
        job=self.get(tenant_id,workspace_id,job_id)
        self._telemetry(job,actor_id,"integration.job.attempt","running",attempt=attempt,metadata={"approval_id":job["approval_id"]})
        try:
            result=connector["handler"](job["action"],job["payload"],job)
            self._update(job_id,tenant_id,workspace_id,status="completed",result=result,reason=None)
            self.events.publish("integration.job.completed",tenant_id,workspace_id,actor_id,"integration_job",job_id,job_id,result or {},trace_id=job["trace_id"],idempotency_key=f"completed:{job_id}")
            self._telemetry(self.get(tenant_id,workspace_id,job_id),actor_id,"integration.job.completed","completed",attempt=attempt)
        except Exception as exc:
            status="dead_letter" if attempt>=self.max_attempts else "failed"
            self._update(job_id,tenant_id,workspace_id,status=status,reason=str(exc),attempts=attempt)
            self.events.publish("integration.job.failed",tenant_id,workspace_id,actor_id,"integration_job",job_id,job_id,
                                {"status":status,"reason":str(exc),"attempts":attempt,"correlation_id":job["correlation_id"]},trace_id=job["trace_id"],idempotency_key=f"failed:{job_id}:{attempt}")
            self._telemetry(self.get(tenant_id,workspace_id,job_id),actor_id,"integration.job.failed",status,attempt=attempt,metadata={"reason":str(exc)})
        return self.get(tenant_id,workspace_id,job_id)
    def retry(self,tenant_id,workspace_id,job_id,actor_id="system"):
        job=self.get(tenant_id,workspace_id,job_id)
        if job["status"] not in ("failed","dead_letter"): return job
        if job["attempts"]>=self.max_attempts: raise ValueError("retry_budget_exhausted")
        self._update(job_id,tenant_id,workspace_id,status="queued",reason=None)
        return self.run(tenant_id,workspace_id,job_id,actor_id)
    def _update(self,job_id,tenant_id,workspace_id,**changes):
        allowed={"status","attempts","result","reason"}
        changes={k:v for k,v in changes.items() if k in allowed}
        if not changes:return
        sets=[]; vals=[]
        for k,v in changes.items():
            col={"result":"result_json"}.get(k,k); sets.append(col+"=?"); vals.append(json.dumps(v,sort_keys=True) if k=="result" else v)
        sets.append("updated_at=?"); vals.append(self._now()); vals += [job_id,str(tenant_id),str(workspace_id)]
        with self._db() as c: c.execute("UPDATE integration_jobs SET "+",".join(sets)+" WHERE job_id=? AND tenant_id=? AND workspace_id=?",vals)
    @staticmethod
    def _row(row):
        d=dict(row); d["payload"]=json.loads(d.pop("payload_json")); raw_result=d.pop("result_json"); d["result"]=json.loads(raw_result) if raw_result else None; return d
    def get(self,t,w,job_id):
        t,w=self._scope(t,w)
        with self._db() as c: row=c.execute("SELECT * FROM integration_jobs WHERE tenant_id=? AND workspace_id=? AND job_id=?",(t,w,job_id)).fetchone()
        if not row: raise ValueError("integration_job_not_found")
        return self._row(row)
    def jobs(self,t,w,limit=100):
        t,w=self._scope(t,w)
        with self._db() as c: rows=c.execute("SELECT * FROM integration_jobs WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",(t,w,max(1,min(int(limit),500)))).fetchall()
        return [self._row(r) for r in rows]
    def reconciliation_queue(self, tenant_id, workspace_id, limit=100):
        t,w=self._scope(tenant_id,workspace_id)
        with self._db() as c:
            rows=c.execute("SELECT * FROM integration_jobs WHERE tenant_id=? AND workspace_id=? AND status IN ('failed','dead_letter') ORDER BY updated_at ASC LIMIT ?",(t,w,max(1,min(int(limit),500)))).fetchall()
        return [self._row(r) for r in rows]

    def replay(self, tenant_id, workspace_id, job_id, actor_id="reconciler"):
        job=self.get(tenant_id,workspace_id,job_id)
        if job["status"] not in ("failed","dead_letter"):
            return job
        if job["attempts"] >= self.max_attempts:
            self._update(job_id,tenant_id,workspace_id,status="queued",attempts=0,reason="reconciliation_reset")
        return self.run(tenant_id,workspace_id,job_id,actor_id)

    def reconcile(self, tenant_id, workspace_id, *, replay=False, limit=100, actor_id="reconciler"):
        queued=self.reconciliation_queue(tenant_id,workspace_id,limit)
        if not replay:
            return {"queued":len(queued),"jobs":queued}
        results=[self.replay(tenant_id,workspace_id,j["job_id"],actor_id) for j in queued]
        return {"queued":len(queued),"replayed":len(results),"results":results}
