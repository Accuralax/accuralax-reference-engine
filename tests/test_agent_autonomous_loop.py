import tempfile
from pathlib import Path
from src.core.agent_autonomous_loop import AgentAutonomousLoop
from src.core.event_bus import EventBus

class Event:
    def __init__(self,i):
        self.event_id=i; self.event_type="sales.lead.created"; self.tenant_id="t"; self.workspace_id="w"
class Events:
    def __init__(self): self.items=[Event("e1")]
    def history(self,*args,**kwargs): return self.items
class Planner:
    def process_event(self,event): return {"plan_id":"p1"}
class Executor:
    def __init__(self,fail=False): self.fail=fail
    def execute(self,*args):
        if self.fail: raise RuntimeError("temporary failure")
        return {"results":[{"status":"completed"}]}
class Replan: pass

def make(d,executor):
    return AgentAutonomousLoop(Planner(),executor,Replan(),Events(),str(Path(d)/"loop.sqlite3"),cycle_budget=2)

def test_processed_event_is_not_repeated():
    with tempfile.TemporaryDirectory() as d:
        loop=make(d,Executor()); assert loop.run("t","w")["events"]==1; assert loop.run("t","w")["events"]==0

def test_failed_event_is_retryable():
    with tempfile.TemporaryDirectory() as d:
        loop=make(d,Executor(True)); assert loop.run("t","w")["events"]==1
        loop.executor=Executor(False); assert loop.run("t","w")["events"]==1
        assert loop.run("t","w")["events"]==0
