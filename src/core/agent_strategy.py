from .agent_outcome_analytics import AgentOutcomeAnalytics

class AgentStrategy:
    def __init__(self, learning, threshold=2):
        self.learning=learning
        self.threshold=max(1,int(threshold))
        self.analytics=AgentOutcomeAnalytics(learning.outcomes, self.threshold)

    def guidance(self, agent_id, tenant_id, workspace_id, query, context_fingerprint=None):
        items=self.learning.recall(agent_id,tenant_id,workspace_id,"",limit=50)
        stats={}
        for item in items:
            text=item.get("content","")
            if " action " not in text or " outcome=" not in text:
                continue
            if context_fingerprint is not None and f"context={context_fingerprint}" not in text:
                continue
            action=text.split(" action ",1)[1].split("=",1)[1].split(" outcome=",1)[0].strip()
            outcome=text.split(" outcome=",1)[1].split(";",1)[0].strip()
            reason_code="unknown"
            if "reason_code=" in text:
                reason_code=text.split("reason_code=",1)[1].split(";",1)[0].strip()
            if reason_code in {"approval_required","policy_blocked"}:
                continue
            row=stats.setdefault(action,{"failed":0,"completed":0,"total":0})
            row["total"]+=1
            row["failed"]+=int(outcome in {"failed","blocked"})
            row["completed"]+=int(outcome=="completed")
        ledger=self.analytics.analyze(tenant_id,workspace_id,context_fingerprint=context_fingerprint)
        avoid=sorted(r["action"] for r in ledger if r["signal"]=="repeat_failure")
        return {"avoid_actions":avoid,"stats":stats,"ledger":ledger,"threshold":self.threshold}
