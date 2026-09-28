import tempfile
from pathlib import Path
from src.core.agent_scheduler import AgentScheduler

class Worker:
    def __init__(self): self.calls=[]
    def run_once(self,t,w): self.calls.append((t,w)); return {"status":"completed"}
    def health(self): return {"status":"ok"}

def test_scheduler_scope_registration_and_tick():
    with tempfile.TemporaryDirectory() as d:
        worker=Worker(); scheduler=AgentScheduler(worker,str(Path(d)/"scheduler.sqlite3"),interval_seconds=1)
        scheduler.register("t","w")
        scheduler._tick()
        assert worker.calls == [("t","w")]
        assert scheduler.status()["runs"] == 1

def test_scheduler_start_stop_is_bounded():
    with tempfile.TemporaryDirectory() as d:
        scheduler=AgentScheduler(Worker(),str(Path(d)/"scheduler.sqlite3"),interval_seconds=60)
        assert scheduler.start()["status"] == "started"
        assert scheduler.start()["status"] == "already_running"
        assert scheduler.stop()["status"] == "stopped"
