import hashlib
from .persistent_memory import PersistentMemory
from .agent_outcome_store import AgentOutcomeStore

class AgentLearningEngine:
    REASON_CODES = ("approval_required","policy_blocked","execution_error","not_found","validation_error","business_condition","unknown")

    @classmethod
    def reason_code(cls, reason=""):
        text=str(reason or "").lower()
        if any(x in text for x in ("approval","consent")): return "approval_required"
        if any(x in text for x in ("policy","permission","denied")): return "policy_blocked"
        if any(x in text for x in ("not found","missing")): return "not_found"
        if any(x in text for x in ("validation","invalid","required")): return "validation_error"
        if any(x in text for x in ("stage","score","condition","business")): return "business_condition"
        if any(x in text for x in ("exception","error","failed")): return "execution_error"
        return "unknown"
    """Turns bounded execution outcomes into governed episodic experience."""
    def __init__(self,memory=None,outcomes=None):
        self.memory=memory or PersistentMemory()
        self.outcomes=outcomes or AgentOutcomeStore()
    def record(self,tenant_id,workspace_id,agent_id,plan_id,feedback):
        outcome=str(feedback.get("outcome","unknown")); counts=feedback.get("counts",{})
        content=f"Plan {plan_id} outcome={outcome}; completed={counts.get('completed',0)}, failed={counts.get('failed',0)}, blocked={counts.get('blocked',0)}, pending={counts.get('pending',0)}."
        return self.memory.write(agent_id,"episodic",content,scope=[str(tenant_id),str(workspace_id),str(plan_id)],provenance=f"plan_executor:{plan_id}",confidence=0.9 if outcome in ("success","failure") else 0.7,importance=0.7,validated=True)
    @staticmethod
    def context_fingerprint(lead=None, opportunity=None, trigger="manual"):
        raw=f"{trigger}|{(lead or {}).get('status','')}|{(lead or {}).get('score','')}|{(opportunity or {}).get('stage','')}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    def record_action(self,tenant_id,workspace_id,agent_id,plan_id,position,action,status,reason="",context_fingerprint="",decision_id=""):
        code=self.reason_code(reason)
        content=f"Plan {plan_id} action {position}={action} outcome={status}; context={context_fingerprint or 'unknown'}; reason_code={code}; reason={reason or 'none'}."
        confidence=0.9 if status == "completed" else (0.75 if code in {"approval_required","policy_blocked"} else 0.8)
        self.outcomes.record(tenant_id,workspace_id,agent_id,plan_id,decision_id,position,action,status,code,reason,context_fingerprint)
        return self.memory.write(agent_id,"episodic",content,scope=[str(tenant_id),str(workspace_id),str(plan_id)],provenance=f"plan_executor:{plan_id}:{position}",confidence=confidence,importance=0.8,validated=True)
    def recall(self,agent_id,tenant_id,workspace_id,query,limit=5):
        items=self.memory.retrieve_ranked(agent_id,query,scope=[str(tenant_id),str(workspace_id)],limit=max(limit*3,limit))
        required={str(tenant_id),str(workspace_id)}
        return [item for item in items if required.issubset(set(item.get("scope",[])))][:limit]
    def health(self): return {"status":"ok","engine":"agent-learning","governed_memory":True,"credentials_stored":False,"scope_exact":True}
