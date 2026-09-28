import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .agent_learning import AgentLearningEngine



class AgentPlanner:
    """Bounded autonomous planning layer. Plans are proposals; execution remains governed."""
    def __init__(self,workflow,db_path=None,max_actions=5,learning=None,pipeline=None,opportunities=None,lms=None):
        self.workflow=workflow; self.learning=learning or AgentLearningEngine()
        self.lms=lms
        self.pipeline=pipeline or getattr(workflow,"pipeline",None)
        self.opportunities=opportunities or getattr(workflow,"opportunities",None)
        self.db_path=db_path or os.path.join("data","agent_planner.sqlite3")
        self.max_actions=max(1,min(int(max_actions),20)); os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS plans(plan_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,trigger TEXT NOT NULL,status TEXT NOT NULL,action_count INTEGER NOT NULL,created_at TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS plan_actions(plan_id TEXT NOT NULL,position INTEGER NOT NULL,decision_id TEXT NOT NULL,action TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(plan_id,position))")
            c.execute("CREATE INDEX IF NOT EXISTS idx_plans_scope ON plans(tenant_id,workspace_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS plan_triggers(event_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,created_at TEXT NOT NULL)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def plan(self,tenant_id,workspace_id,client_id,lead=None,opportunity=None,consent_granted=False,open_tasks=0,trigger="manual",agent_id="default"):
        query=str(trigger)+" "+str((lead or {}).get("status",""))+" "+str((lead or {}).get("score",""))+" "+str((opportunity or {}).get("stage",""))
        experience=self.learning.recall(agent_id,tenant_id,workspace_id,query,limit=5)
        from .agent_strategy import AgentStrategy
        context_fingerprint=self.learning.context_fingerprint(lead,opportunity,trigger)
        guidance=AgentStrategy(self.learning).guidance(agent_id,tenant_id,workspace_id,query,context_fingerprint)
        decision_set=self.workflow.decide(tenant_id,workspace_id,client_id,lead,opportunity,consent_granted,open_tasks)
        actions=[]
        for item in decision_set["next_actions"][:self.max_actions]:
            if item.get("action") in guidance["avoid_actions"] and item.get("action") != "request_consent":
                item=dict(item); item["action"]="review"; item["reason"]="learning_repeat_failure_requires_review"
            item=dict(item)
            item["context_fingerprint"]=context_fingerprint
            actions.append(item)
        pid="PLN-"+uuid.uuid4().hex[:16].upper(); now=datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("INSERT INTO plans VALUES(?,?,?,?,?,?,?)",(pid,str(tenant_id),str(workspace_id),str(trigger),"proposed",len(actions),now))
            for pos,item in enumerate(actions,1): c.execute("INSERT INTO plan_actions VALUES(?,?,?,?,?)",(pid,pos,item["decision_id"],item["action"],"pending"))
        return {"plan_id":pid,"status":"proposed","trigger":trigger,"action_budget":self.max_actions,"actions":actions,"learned_experience":experience,"learning_guidance":guidance}
    def plan_from_event(self,event,lead=None,opportunity=None,consent_granted=False,open_tasks=0):
        payload=event.payload or {}
        client_id=str(payload.get("client_id") or event.entity_id)
        if event.event_type.startswith("sales.lead") and self.pipeline:
            lead=lead or self.pipeline.get_lead(event.tenant_id,event.workspace_id,event.entity_id)
            client_id=str((lead or {}).get("client_id") or client_id)
        if event.event_type.startswith("sales.opportunity") and self.opportunities:
            opportunity=opportunity or self.opportunities.get(event.tenant_id,event.workspace_id,event.entity_id)
            client_id=str((opportunity or {}).get("client_id") or client_id)
        with self._db() as c: row=c.execute("SELECT plan_id FROM plan_triggers WHERE event_id=?",(event.event_id,)).fetchone()
        if row:
            existing=self.get(event.tenant_id,event.workspace_id,row[0]); return {"plan_id":row[0],"status":existing["plan"]["status"],"trigger":existing["plan"]["trigger"],"action_budget":self.max_actions,"actions":existing["actions"]}
        result=self.plan(event.tenant_id,event.workspace_id,client_id,lead,opportunity,consent_granted,open_tasks,trigger=event.event_type)
        with self._db() as c: c.execute("INSERT OR IGNORE INTO plan_triggers VALUES(?,?,?)",(event.event_id,result["plan_id"],datetime.now(timezone.utc).isoformat()))
        return result
    def process_pending_events(self,tenant_id,workspace_id,limit=100):
        allowed={"sales.lead.created","sales.lead.stage_changed","sales.opportunity.created","sales.opportunity.stage_changed","lms.progress.recorded","lms.attendance.recorded","lms.assessment.status_changed"}; results=[]
        for event in reversed(self.workflow.events.history(str(tenant_id),str(workspace_id),limit=limit)):
            if event.event_type in allowed: results.append(self.process_event(event))
        return {"processed":len(results),"plans":results}
    def set_status(self,tenant_id,workspace_id,plan_id,status):
        if status not in {"proposed","partial","completed","failed","cancelled"}: raise ValueError("invalid_plan_status")
        with self._db() as c: updated=c.execute("UPDATE plans SET status=? WHERE tenant_id=? AND workspace_id=? AND plan_id=?",(status,str(tenant_id),str(workspace_id),str(plan_id))).rowcount
        if not updated: raise ValueError("plan_not_found")
        return self.get(tenant_id,workspace_id,plan_id)
    def get(self,tenant_id,workspace_id,plan_id):
        with self._db() as c:
            p=c.execute("SELECT * FROM plans WHERE tenant_id=? AND workspace_id=? AND plan_id=?",(str(tenant_id),str(workspace_id),str(plan_id))).fetchone()
            if not p: raise ValueError("plan_not_found")
            a=c.execute("SELECT * FROM plan_actions WHERE plan_id=? ORDER BY position",(plan_id,)).fetchall()
        return {"plan":dict(p),"actions":[dict(x) for x in a]}
    def process_event(self,event,lead=None,opportunity=None,consent_granted=False,open_tasks=0):
        allowed={"sales.lead.created","sales.lead.stage_changed","sales.opportunity.created","sales.opportunity.stage_changed","lms.progress.recorded","lms.attendance.recorded","lms.assessment.status_changed"}
        if event.event_type not in allowed: return {"status":"ignored","reason":"event_not_plannable"}
        return self.plan_from_event(event,lead,opportunity,consent_granted,open_tasks)
    def health(self):
        with self._db() as c: count=c.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        return {"status":"ok","engine":"agent-planner","bounded":True,"max_actions":self.max_actions,"plans":count,"execution_separate":True,"learning_connected":True}
