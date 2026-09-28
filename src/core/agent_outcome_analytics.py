from .agent_outcome_store import AgentOutcomeStore

class AgentOutcomeAnalytics:
    """Evidence-based strategy signals over the durable outcome ledger."""
    def __init__(self, store=None, min_samples=2):
        self.store=store or AgentOutcomeStore()
        self.min_samples=max(1,int(min_samples))

    def analyze(self, tenant_id, workspace_id, action=None, context_fingerprint=None):
        stats=self.store.stats(tenant_id,workspace_id,action,context_fingerprint)
        findings=[]
        for name,row in stats.items():
            total=row["total"]
            completed=row.get("completed",0)+row.get("already_executed",0)
            failed=row.get("failed",0)
            blocked=row.get("blocked",0)
            effective=max(0,total-blocked)
            success_rate=completed/effective if effective else 0.0
            failure_rate=failed/effective if effective else 0.0
            if total < self.min_samples:
                signal="insufficient_evidence"
            elif failure_rate >= 0.5 and failed > completed:
                signal="repeat_failure"
            elif success_rate >= 0.7:
                signal="stable_success"
            else:
                signal="mixed"
            findings.append({"action":name,"total":total,"completed":completed,"failed":failed,
                             "blocked":blocked,"success_rate":round(success_rate,4),
                             "failure_rate":round(failure_rate,4),"signal":signal})
        return sorted(findings,key=lambda x:(x["signal"]!="repeat_failure",-x["total"],x["action"]))

    def recommendations(self, tenant_id, workspace_id, context_fingerprint=None):
        rows=self.analyze(tenant_id,workspace_id,context_fingerprint=context_fingerprint)
        return [{"action":r["action"],"recommendation":"review_before_retry" if r["signal"]=="repeat_failure" else
                 "continue" if r["signal"]=="stable_success" else "observe",
                 "evidence":r} for r in rows]

    def health(self):
        return {"status":"ok","engine":"agent-outcome-analytics","evidence_threshold":self.min_samples}
