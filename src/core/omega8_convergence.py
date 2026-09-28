# Ω-8.4 → Ω-8.15 convergence control plane
from datetime import datetime, timezone

class Omega8Convergence:
    """Coordinates the existing bounded agent layers into one auditable lifecycle."""
    def __init__(self, learning=None, strategy=None, memory=None, evaluation=None, registry=None, governance=None, replanning=None, approval=None, audit=None, observability=None):
        self.learning=learning; self.strategy=strategy; self.memory=memory; self.evaluation=evaluation
        self.registry=registry; self.governance=governance; self.replanning=replanning; self.approval=approval
        self.audit=audit; self.observability=observability

    def outcome_learning(self, tenant_id, workspace_id, agent_id, plan_id, feedback):
        if not self.learning: return {"status":"blocked","reason":"learning_engine_missing"}
        recorded=self.learning.record(tenant_id,workspace_id,agent_id,plan_id,feedback)
        return {"status":"recorded","feedback":feedback,"learning":recorded}

    def strategy_guidance(self, agent_id, tenant_id, workspace_id, query, context_fingerprint=None):
        if not self.strategy: return {"status":"blocked","reason":"strategy_engine_missing"}
        return {"status":"ready","guidance":self.strategy.guidance(agent_id,tenant_id,workspace_id,query,context_fingerprint)}

    def consolidate_memory(self, agent_id):
        if not self.memory: return {"status":"blocked","reason":"memory_engine_missing"}
        return self.memory.consolidate(agent_id)

    def evaluate(self, tenant_id, workspace_id, **kwargs):
        if not self.evaluation: return {"status":"blocked","reason":"evaluation_engine_missing"}
        return self.evaluation.evaluate(tenant_id,workspace_id,**kwargs)

    def govern(self, tenant_id, workspace_id, agent_id, action, **kwargs):
        if not self.governance: return {"status":"blocked","reason":"governance_engine_missing"}
        return self.governance.check(tenant_id,workspace_id,agent_id,action,**kwargs)

    def lifecycle(self, tenant_id, workspace_id, agent_id):
        if not self.registry: return {"status":"blocked","reason":"registry_missing"}
        agent=self.registry.get_agent(tenant_id,workspace_id,agent_id)
        if not agent: return {"status":"blocked","reason":"agent_not_found"}
        return {"status":"ready","agent":agent}

    def observe(self, tenant_id, workspace_id, event_type, metadata=None, trace_id=None, correlation_id=None):
        result={"status":"recorded"}
        if self.audit:
            result["audit"]=self.audit.record(tenant_id,workspace_id,"agent",event_type,source="omega8",metadata=metadata,trace_id=trace_id,correlation_id=correlation_id)
        if self.observability:
            result["log"]=self.observability.log(tenant_id,workspace_id,"INFO",event_type,trace_id=trace_id,correlation_id=correlation_id,metadata=metadata)
        return result

    def health(self):
        return {"status":"ok","layers":"omega8.4-omega8.15","learning":bool(self.learning),"strategy":bool(self.strategy),"memory":bool(self.memory),"evaluation":bool(self.evaluation),"registry":bool(self.registry),"governance":bool(self.governance),"replanning":bool(self.replanning),"approval":bool(self.approval),"audit":bool(self.audit),"observability":bool(self.observability),"execution_boundary":True,"timestamp":datetime.now(timezone.utc).isoformat()}
