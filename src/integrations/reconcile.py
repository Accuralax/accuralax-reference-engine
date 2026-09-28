from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from core.enterprise_integration_layer import EnterpriseIntegrationLayer
from .retry_policy import RetryPolicy

@dataclass(frozen=True)
class ReconcileBatch:
    scanned:int
    replayed:int
    completed:int
    failed:int
    dead_letter:int
    skipped:int
    results:tuple[dict[str,Any],...]
    def public(self):
        return {"scanned":self.scanned,"replayed":self.replayed,"completed":self.completed,"failed":self.failed,"dead_letter":self.dead_letter,"skipped":self.skipped,"results":list(self.results)}

class IntegrationReconciler:
    """Bounded, tenant-scoped replay worker."""
    def __init__(self,durable:EnterpriseIntegrationLayer,policy:RetryPolicy|None=None,*,actor_id="reconciliation-worker",sleep_fn:Callable[[float],None]|None=None):
        self.durable=durable
        self.policy=policy or RetryPolicy(max_attempts=durable.max_attempts)
        self.actor_id=actor_id
        self.sleep_fn=sleep_fn or (lambda _:None)
    def run_once(self,tenant_id,workspace_id,*,limit=100,replay_dead_letter=False):
        queue=self.durable.reconciliation_queue(tenant_id,workspace_id,limit=limit)
        results=[]
        for job in queue:
            if job["status"]=="dead_letter" and not replay_dead_letter:
                results.append({**job,"reconciliation":"skipped_dead_letter"}); continue
            self.sleep_fn(self.policy.delay(max(1,int(job["attempts"]))))
            results.append(self.durable.replay(tenant_id,workspace_id,job["job_id"],self.actor_id))
        completed=sum(r["status"]=="completed" for r in results)
        failed=sum(r["status"]=="failed" for r in results)
        dead=sum(r["status"]=="dead_letter" for r in results)
        skipped=sum(r.get("reconciliation")=="skipped_dead_letter" for r in results)
        return ReconcileBatch(len(queue),len(queue)-skipped,completed,failed,dead,skipped,tuple(results))
    def run_until_stable(self,tenant_id,workspace_id,*,limit=100,max_cycles=10,replay_dead_letter=False):
        if max_cycles<1: raise ValueError("max_cycles_must_be_positive")
        batches=[]
        for _ in range(max_cycles):
            b=self.run_once(tenant_id,workspace_id,limit=limit,replay_dead_letter=replay_dead_letter)
            batches.append(b.public())
            if b.scanned==0 or (b.replayed==0 and b.failed==0): break
        return batches
