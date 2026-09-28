from __future__ import annotations
from collections import Counter
from typing import Any
from core.observability import Observability

class IntegrationObservability:
    def __init__(self,store:Observability):
        self.store=store
    def record_job(self,job:dict[str,Any]):
        labels={"connector":job.get("connector"),"action":job.get("action"),"status":job.get("status")}
        self.store.metric(job["tenant_id"],job["workspace_id"],"integration.jobs",1,labels)
        if job.get("status") in {"failed","dead_letter"}:
            self.store.metric(job["tenant_id"],job["workspace_id"],"integration.failures",1,labels)
        self.store.log(job["tenant_id"],job["workspace_id"],"INFO",f"integration.job.{job.get('status','unknown')}",trace_id=job.get("trace_id"),correlation_id=job.get("correlation_id"),metadata={"job_id":job.get("job_id"),"connector":job.get("connector"),"action":job.get("action"),"attempts":job.get("attempts")})
    def record_queue_depth(self,tenant_id,workspace_id,depth):
        return self.store.metric(tenant_id,workspace_id,"integration.reconciliation.queue_depth",max(0,int(depth)))

    def record_reconciliation(self,tenant_id,workspace_id,batch):
        values={"scanned":batch.scanned,"replayed":batch.replayed,"completed":batch.completed,"failed":batch.failed,"dead_letter":batch.dead_letter,"skipped":batch.skipped}
        for key,value in values.items():
            self.store.metric(tenant_id,workspace_id,"integration.reconciliation."+key,value)
        self.store.metric(tenant_id,workspace_id,"integration.retry.attempts",sum(int(r.get("attempts",0)) for r in batch.results))
        self.store.log(tenant_id,workspace_id,"INFO","integration.reconciliation.completed",metadata=values)
        return values

    def snapshot(self,tenant_id,workspace_id):
        snap=self.store.snapshot(tenant_id,workspace_id); counts=Counter()
        for row in snap["metrics"]: counts[row["name"]]+=row["value"]
        return {"tenant_id":str(tenant_id),"workspace_id":str(workspace_id),"metric_totals":dict(counts),"logs":len(snap["logs"]),"traces":len(snap["traces"])}
