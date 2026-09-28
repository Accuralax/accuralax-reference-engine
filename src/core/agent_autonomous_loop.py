import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus
from .agent_event_context import AgentEventContext


class AgentAutonomousLoop:
    """Bounded event-to-plan loop; approvals remain a hard execution boundary."""
    def __init__(self, planner, executor, replanning, event_bus=None, db_path=None, cycle_budget=10):
        self.planner=planner; self.executor=executor; self.replanning=replanning
        self.events=event_bus or EventBus()
        self.context=AgentEventContext(getattr(planner, "workflow", None), getattr(planner, "lms", None))
        self.db_path=db_path or os.path.join("data","agent_autonomous_loop.sqlite3")
        self.cycle_budget=max(1,min(int(cycle_budget),50)); os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS loop_runs(run_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,status TEXT,event_count INTEGER,plan_count INTEGER,execution_count INTEGER,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS loop_events(run_id TEXT,event_id TEXT,tenant_id TEXT,workspace_id TEXT,status TEXT,plan_id TEXT,processed_at TEXT,PRIMARY KEY(run_id,event_id))")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_loop_event_once ON loop_events(tenant_id,workspace_id,event_id)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def _seen(self,t,w,e):
        with self._db() as c:
            row=c.execute("SELECT status FROM loop_events WHERE tenant_id=? AND workspace_id=? AND event_id=?",(str(t),str(w),str(e))).fetchone()
            return bool(row and row["status"] == "processed")
    def _mark(self,run_id,event,status,plan_id=""):
        with self._db() as c:
            c.execute("INSERT INTO loop_events VALUES(?,?,?,?,?,?,?) ON CONFLICT(tenant_id,workspace_id,event_id) DO UPDATE SET run_id=excluded.run_id,status=excluded.status,plan_id=excluded.plan_id,processed_at=excluded.processed_at",(run_id,event.event_id,event.tenant_id,event.workspace_id,status,plan_id,datetime.now(timezone.utc).isoformat()))
    def run(self,tenant_id,workspace_id,limit=None):
        budget=min(self.cycle_budget,max(1,int(limit or self.cycle_budget))); run_id="LOOP-"+uuid.uuid4().hex[:16].upper()
        with self._db() as c: c.execute("INSERT INTO loop_runs VALUES(?,?,?,?,?,?,?,?)",(run_id,str(tenant_id),str(workspace_id),"running",0,0,0,datetime.now(timezone.utc).isoformat()))
        allowed={"sales.lead.created","sales.lead.stage_changed","sales.opportunity.created","sales.opportunity.stage_changed","lms.progress.recorded","lms.attendance.recorded","lms.assessment.status_changed","compliance.assessment.requested"}
        events=[e for e in reversed(self.events.history(str(tenant_id),str(workspace_id),limit=min(500,budget*3))) if e.event_type in allowed and not self._seen(tenant_id,workspace_id,e.event_id)][:budget]
        results=[]; plans=0; executions=0
        for event in events:
            try:
                if event.event_type == "compliance.assessment.requested" and hasattr(self.planner, "compliance_orchestrator"):
                    result = self.planner.compliance_orchestrator.process_event(event)
                    self._mark(run_id,event,"processed",result.get("run_id", ""))
                    results.append({"event_id":event.event_id,"compliance":result})
                    continue
                if getattr(self.planner, "workflow", None):
                    context=self.context.resolve(event)
                    plan=self.planner.process_event(event, lead=context.get("lead"), opportunity=context.get("opportunity"))
                else:
                    plan=self.planner.process_event(event)
                plans+=1
                action_results=self.executor.execute(str(tenant_id),str(workspace_id),plan["plan_id"])
                executions+=len(action_results.get("results",[]))
                self._mark(run_id,event,"processed",plan["plan_id"])
                results.append({"event_id":event.event_id,"plan_id":plan["plan_id"],"execution":action_results})
            except Exception as exc:
                self._mark(run_id,event,"failed")
                results.append({"event_id":event.event_id,"status":"failed","reason":str(exc)})
        status="completed"
        with self._db() as c: c.execute("UPDATE loop_runs SET status=?,event_count=?,plan_count=?,execution_count=? WHERE run_id=?",(status,len(events),plans,executions,run_id))
        return {"run_id":run_id,"status":status,"budget":budget,"events":len(events),"plans":plans,"executions":executions,"results":results}
    def health(self):
        with self._db() as c: runs=c.execute("SELECT COUNT(*) FROM loop_runs").fetchone()[0]
        return {"status":"ok","engine":"agent-autonomous-loop","bounded":True,"cycle_budget":self.cycle_budget,"approval_boundary":True,"runs":runs}
