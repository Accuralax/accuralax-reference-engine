import tempfile
from pathlib import Path
from src.core.agent_event_worker import AgentEventWorker
from src.core.event_bus import EventBus

class Loop:
    def __init__(self,bus): self.events=bus; self.calls=0
    def run(self,t,w,limit=None): self.calls+=1; return {"events":min(limit or 1,1),"status":"completed"}

def make(d):
    bus=EventBus(str(Path(d)/"events.sqlite3")); loop=Loop(bus)
    worker=AgentEventWorker(loop,bus,str(Path(d)/"worker.sqlite3"),batch_size=2,lease_seconds=10)
    return bus,loop,worker

def test_worker_processes_and_persists_state():
    with tempfile.TemporaryDirectory() as d:
        bus,loop,worker=make(d); bus.publish("sales.lead.created","t","w","a","lead","1","r",{})
        result=worker.run_once("t","w")
        assert result["status"] == "completed" and result["processed"] == 1
        assert worker.state("t","w")["status"] == "idle"

def test_worker_scope_and_lease():
    with tempfile.TemporaryDirectory() as d:
        _,_,worker=make(d); first=worker.run_once("t1","w")
        assert first["status"] == "completed" and worker.state("t2","w")["status"] == "idle"

def test_stale_run_is_recovered():
    with tempfile.TemporaryDirectory() as d:
        _,_,worker=make(d)
        with worker._db() as c:
            c.execute("INSERT INTO worker_runs VALUES(?,?,?,?,?,?,?,?)",("WRK-old","t","w","running",0,"2020-01-01T00:00:00+00:00",None,None))
            c.execute("INSERT INTO worker_state VALUES(?,?,?,?,?,?,?)",("t","w","running","WRK-old","2020-01-01T00:00:00+00:00",None,"2020-01-01T00:00:01+00:00"))
        result=worker.recover_stale("t","w")
        assert result["recovered"] is True
        assert worker.state("t","w")["status"] == "recovered"
        with worker._db() as c: assert c.execute("SELECT status FROM worker_runs WHERE run_id='WRK-old'").fetchone()[0] == "interrupted"
