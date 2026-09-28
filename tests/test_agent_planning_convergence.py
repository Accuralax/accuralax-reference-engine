import tempfile
from types import SimpleNamespace
from src.core.agent_planning_convergence import AgentPlanningConvergence

class Signals:
    def ingest(self, event): return {"signal_id":"SIG-1","tenant_id":event.tenant_id,"workspace_id":event.workspace_id}

class Decisions:
    def decide(self, *args, **kwargs): return {"decision_id":"DEC-1","status":"approved","execution_allowed":False}

class Planner:
    def plan(self, *args, **kwargs): return {"plan_id":"PLN-1","status":"proposed","actions":[{"decision_id":"D1","action":"review","risk":"read"}]}

class Replanner:
    def __init__(self): self.calls=0
    def propose(self,*args,**kwargs): self.calls += 1; return {"status":"proposed","new_plan_id":"PLN-2"}

class Governance:
    def check(self,*args,**kwargs): return {"allowed":False,"approval_required":True,"reason":"high_risk_requires_approval"}

def event():
    return SimpleNamespace(tenant_id="t1",workspace_id="w1",event_id="e1",event_type="security.alert",entity_id="x1",payload={"client_id":"c1"})

def test_selection_is_bounded_and_deterministic():
    c=AgentPlanningConvergence(Signals(),Decisions(),Planner(),Replanner(),max_agents=2)
    r=c.select_agent([{"agent_id":"b","confidence":.7},{"agent_id":"a","confidence":.9},{"agent_id":"z","confidence":1}])
    assert r["agent_id"]=="a" and r["candidates_considered"]==2

def test_pipeline_stops_at_governance_approval():
    c=AgentPlanningConvergence(Signals(),Decisions(),Planner(),Replanner(),governance=Governance())
    r=c.run(event(),[{"agent_id":"a","confidence":1}],risk="execute")
    assert r["stage"]=="governance"
    assert r["status"]=="approval_required"

def test_replan_delegates_to_bounded_engine():
    rp=Replanner(); c=AgentPlanningConvergence(Signals(),Decisions(),Planner(),rp)
    r=c.replan("t1","w1","PLN-1")
    assert r["status"]=="proposed" and rp.calls==1

def test_health_declares_execution_boundary():
    c=AgentPlanningConvergence(Signals(),Decisions(),Planner(),Replanner(),max_cycles=4)
    h=c.health()
    assert h["status"]=="ok" and h["max_cycles"]==4 and h["execution_separate"] is True
