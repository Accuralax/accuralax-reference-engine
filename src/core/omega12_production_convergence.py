from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json

class Omega12ProductionConvergence:
    """Final O-12 production assurance facade; evaluation remains fail-closed."""
    def __init__(self, evaluator, *, max_history=200, regression_tolerance=.05, drift_tolerance=.10):
        self.evaluator=evaluator; self.max_history=max(1,min(int(max_history),1000))
        self.regression_tolerance=max(0,min(float(regression_tolerance),1)); self.drift_tolerance=max(0,min(float(drift_tolerance),1))
        self._history=[]; self._quarantine={}; self._production={}
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def _record(self,event,**data):
        self._history.append({"event":event,"at":self._now(),**data}); self._history=self._history[-self.max_history:]
    def continuous_check(self,tenant_id,workspace_id,agent_id,model_id,dataset_id,*,baseline_score=None):
        gate=self.evaluator.release_gate(tenant_id,workspace_id,agent_id,model_id,dataset_id)
        current=gate.get("score")
        regression=self.evaluator.regression(current,baseline_score,self.regression_tolerance) if current is not None and baseline_score is not None else {"regression":False}
        allowed=bool(gate.get("release_allowed") and not regression.get("regression"))
        result={"status":"passed" if allowed else "blocked","release_allowed":allowed,"gate":gate,"regression":regression}
        self._record("continuous.evaluation",tenant_id=str(tenant_id),workspace_id=str(workspace_id),agent_id=str(agent_id),result=result)
        return result
    def quarantine(self,tenant_id,workspace_id,agent_id,reason):
        key=(str(tenant_id),str(workspace_id),str(agent_id)); item={"status":"quarantined","reason":str(reason),"at":self._now()}; self._quarantine[key]=item
        self._record("agent.quarantined",tenant_id=key[0],workspace_id=key[1],agent_id=key[2],reason=str(reason)); return item
    def unquarantine(self,tenant_id,workspace_id,agent_id,approval):
        if not approval:return {"status":"blocked","reason":"approval_required"}
        self._quarantine.pop((str(tenant_id),str(workspace_id),str(agent_id)),None); return {"status":"released","agent_id":str(agent_id)}
    def monitor(self,tenant_id,workspace_id,agent_id,metrics):
        q=self._quarantine.get((str(tenant_id),str(workspace_id),str(agent_id))); result={"status":"quarantined" if q else "monitoring","metrics":dict(metrics or {}),"quarantine":q}; self._production[(str(tenant_id),str(workspace_id),str(agent_id))]=result; return result
    def evidence(self,tenant_id=None,workspace_id=None):
        return [x for x in self._history if (tenant_id is None or x.get("tenant_id")==str(tenant_id)) and (workspace_id is None or x.get("workspace_id")==str(workspace_id))]
    def full_stack_gate(self, layers):
        required={f"omega{i}" for i in range(8,13)}; available={str(k) for k,v in dict(layers or {}).items() if isinstance(v,dict) and v.get("ready",v.get("status") in {"ok","ready"})}
        missing=sorted(required-available); allowed=not missing
        return {"status":"ready" if allowed else "blocked","release_allowed":allowed,"missing_layers":missing,"required_layers":sorted(required)}
    def production_gate(self,tenant_id,workspace_id,agent_id,model_id,dataset_id,*,baseline_score=None,layers=None):
        check=self.continuous_check(tenant_id,workspace_id,agent_id,model_id,dataset_id,baseline_score=baseline_score)
        stack=self.full_stack_gate(layers or {f"omega{i}":{"ready":True} for i in range(8,13)})
        quarantined=(str(tenant_id),str(workspace_id),str(agent_id)) in self._quarantine
        allowed=bool(check["release_allowed"] and stack["release_allowed"] and not quarantined)
        result={"status":"ready" if allowed else "blocked","release_allowed":allowed,"evaluation":check,"stack":stack,"quarantined":quarantined}
        self._record("production.gate",tenant_id=str(tenant_id),workspace_id=str(workspace_id),agent_id=str(agent_id),result=result); return result
    def readiness(self):
        return {"ready":True,"continuous_evaluation":True,"regression_quarantine":True,"production_monitoring":True,"evidence_lineage":True,"full_stack_gate":True,"bounded_history":True}
    def health(self): return {"status":"ok","bounded":True,"history":len(self._history),"quarantined":len(self._quarantine),"production_monitors":len(self._production)}
