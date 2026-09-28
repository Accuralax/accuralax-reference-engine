from __future__ import annotations
from datetime import datetime, timezone

class Omega8FullConvergence:
    """Ω-8.5..Ω-8.15: bounded strategy, delegation, memory, evaluation, governance, lifecycle, recovery, approval, audit and release convergence."""
    def __init__(self, strategy=None, memory=None, evaluation=None, registry=None, governance=None, recovery=None, approval=None, audit=None, observability=None, invariants=None, max_delegates=5, max_replans=3):
        self.strategy=strategy; self.memory=memory; self.evaluation=evaluation; self.registry=registry; self.governance=governance
        self.recovery=recovery; self.approval=approval; self.audit=audit; self.observability=observability; self.invariants=invariants
        self.max_delegates=max(1,min(int(max_delegates),10)); self.max_replans=max(1,min(int(max_replans),10))

    # Ω-8.5
    def adaptive_strategy(self, agent_id, tenant_id, workspace_id, query, context_fingerprint=None):
        if not self.strategy: return {"status":"blocked","reason":"strategy_missing"}
        guidance=self.strategy.guidance(agent_id,tenant_id,workspace_id,query,context_fingerprint)
        return {"status":"ready","strategy":guidance,"bounded":True}

    # Ω-8.6
    def delegate(self, tasks, available_agents):
        tasks=list(tasks or []); agents=list(available_agents or [])[:self.max_delegates]
        if not agents: return {"status":"blocked","reason":"no_agents"}
        assignments=[]
        for i,task in enumerate(tasks[:self.max_delegates]):
            agent=sorted(agents,key=lambda a:(-float(a.get("confidence",0)),str(a.get("agent_id",""))))[i % len(agents)]
            assignments.append({"task_id":task.get("task_id",f"TASK-{i+1}"),"agent_id":agent.get("agent_id"),"status":"delegated"})
        return {"status":"delegated","assignments":assignments,"bounded":True}

    # Ω-8.7
    def consolidate(self, agent_id):
        if not self.memory: return {"status":"blocked","reason":"memory_missing"}
        return self.memory.consolidate(agent_id)

    # Ω-8.8
    def evaluate(self, tenant_id, workspace_id, **kwargs):
        if not self.evaluation: return {"status":"blocked","reason":"evaluation_missing"}
        return self.evaluation.evaluate(tenant_id,workspace_id,**kwargs)

    # Ω-8.9
    def govern(self, tenant_id, workspace_id, agent_id, action, **kwargs):
        if not self.governance: return {"status":"blocked","reason":"governance_missing"}
        return self.governance.check(tenant_id,workspace_id,agent_id,action,**kwargs)

    # Ω-8.10
    def lifecycle(self, tenant_id, workspace_id, agent_id):
        if not self.registry: return {"status":"blocked","reason":"registry_missing"}
        agent=self.registry.get_agent(tenant_id,workspace_id,agent_id)
        return {"status":"ready","agent":agent} if agent else {"status":"blocked","reason":"agent_not_found"}

    # Ω-8.11
    def recover(self, operation_id, operation, reconcile=None):
        if not self.recovery: return {"status":"blocked","reason":"recovery_missing"}
        return self.recovery.recover(operation_id,operation,reconcile)

    # Ω-8.12
    def request_approval(self, tenant_id, workspace_id, plan_id, position, decision_id, reason=""):
        if not self.approval: return {"status":"blocked","reason":"approval_missing"}
        return self.approval.request(tenant_id,workspace_id,plan_id,position,decision_id,"system",reason)

    # Ω-8.13
    def observe(self, tenant_id, workspace_id, event_type, metadata=None, trace_id=None, correlation_id=None):
        out={"status":"recorded"}
        if self.audit: out["audit"]=self.audit.record(tenant_id,workspace_id,"agent",event_type,source="omega8",metadata=metadata,trace_id=trace_id,correlation_id=correlation_id)
        if self.observability: out["log"]=self.observability.log(tenant_id,workspace_id,"INFO",event_type,trace_id=trace_id,correlation_id=correlation_id,metadata=metadata)
        return out

    # Ω-8.14
    def end_to_end(self, stages):
        required=("signal","decision","agent","plan","evaluation","governance","approval","execution","outcome","learning")
        missing=[x for x in required if x not in stages]
        if missing: return {"status":"blocked","reason":"missing_stages","missing":missing}
        blocked=[x for x in required if isinstance(stages[x],dict) and stages[x].get("status") in {"blocked","failed"}]
        return {"status":"blocked" if blocked else "converged","blocked_stages":blocked,"stage_count":len(required)}

    # Ω-8.15
    def release_gate(self):
        if not self.invariants: return {"status":"blocked","reason":"invariants_missing","release_allowed":False}
        result=self.invariants.evaluate()
        return {"status":"released" if result["release_allowed"] else "blocked","release_allowed":result["release_allowed"],"invariants":result}

    def health(self):
        return {"status":"ok","layers":"omega8.5-omega8.15","bounded":True,"max_delegates":self.max_delegates,"max_replans":self.max_replans,"fail_closed_release":True,"execution_boundary":True,"timestamp":datetime.now(timezone.utc).isoformat()}
