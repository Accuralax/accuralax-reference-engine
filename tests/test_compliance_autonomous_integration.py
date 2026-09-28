import tempfile
from pathlib import Path
from src.core.agent_autonomous_loop import AgentAutonomousLoop
from src.core.event_bus import EventBus

class Event:
    def __init__(self, i):
        self.event_id=i
        self.event_type="compliance.assessment.requested"
        self.tenant_id="t"; self.workspace_id="w"; self.actor_id="tester"; self.entity_id="compliance"
        self.payload={"requested_by":"tester"}

class Compliance:
    def __init__(self): self.calls=0
    def process_event(self,event):
        self.calls+=1
        return {"status":"assessed","run_id":"COR-test"}

class Planner:
    def __init__(self, compliance):
        self.compliance_orchestrator=compliance
        self.workflow=None

class Executor: pass
class Replan: pass

class Events:
    def __init__(self): self.items=[Event("ce1")]
    def history(self,*args,**kwargs): return self.items

def test_compliance_event_enters_autonomous_loop_once():
    with tempfile.TemporaryDirectory() as d:
        compliance=Compliance()
        loop=AgentAutonomousLoop(Planner(compliance),Executor(),Replan(),Events(),str(Path(d)/"loop.sqlite3"),cycle_budget=2)
        first=loop.run("t","w")
        second=loop.run("t","w")
        assert first["events"]==1
        assert first["plans"]==0
        assert first["executions"]==0
        assert first["results"][0]["compliance"]["status"]=="assessed"
        assert second["events"]==0
        assert compliance.calls==1
