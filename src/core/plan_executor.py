import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .human_approval import HumanApprovalGateway
from .event_bus import EventBus
from .agent_learning import AgentLearningEngine

class PlanExecutor:
    """Executes only approved plan actions through the existing governed workflow."""
    def __init__(self, planner, workflow, approvals=None, db_path=None, max_actions=5, learning=None, execution_gate=None, governance=None):
        self.planner = planner
        self.workflow = workflow
        self.approvals = approvals or HumanApprovalGateway()
        self.db_path = db_path or os.path.join("data", "plan_executor.sqlite3")
        self.max_actions = max(1, min(int(max_actions), 20))
        self.learning = learning or getattr(planner, "learning", None) or AgentLearningEngine()
        self.execution_gate = execution_gate
        self.governance = governance
        self.events = EventBus(os.path.join(os.path.dirname(self.db_path) or ".", "event_bus.sqlite3"))
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS executions(
                plan_id TEXT NOT NULL, position INTEGER NOT NULL, tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, decision_id TEXT NOT NULL, status TEXT NOT NULL,
                started_at TEXT, finished_at TEXT, approval_id TEXT, result_json TEXT,
                PRIMARY KEY(plan_id,position))""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_execution_scope ON executions(tenant_id,workspace_id,status)")

    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path)
        c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _execution(self, tenant_id, workspace_id, plan_id, position):
        with self._db() as c:
            return c.execute("""SELECT * FROM executions WHERE tenant_id=? AND workspace_id=?
                AND plan_id=? AND position=?""",
                (str(tenant_id),str(workspace_id),str(plan_id),int(position))).fetchone()

    def request_approval(self, tenant_id, workspace_id, plan_id, position, requested_by="system"):
        plan = self.planner.get(tenant_id, workspace_id, plan_id)
        if position < 1 or position > len(plan["actions"]):
            raise ValueError("plan_action_not_found")
        action = plan["actions"][position-1]
        return self.approvals.request(tenant_id, workspace_id, plan_id, position,
                                      action["decision_id"], requested_by, action["reason"])

    def execute(self, tenant_id, workspace_id, plan_id, approver_id=None, owner_id=None,
                task=None, opportunity=None, changed_by="agent"):
        plan = self.planner.get(tenant_id, workspace_id, plan_id)
        if plan["plan"]["status"] in ("rejected", "cancelled"):
            return {"status":"blocked", "reason":"plan_not_executable", "plan_id":plan_id}
        actions = plan["actions"][:self.max_actions]
        results=[]
        for position, action in enumerate(actions,1):
            existing=self._execution(tenant_id,workspace_id,plan_id,position)
            if existing and existing["status"] == "completed":
                results.append(dict(existing)); continue
            approval=self.approvals.for_action(tenant_id,workspace_id,plan_id,position)
            if not approval or approval["status"] != "approved":
                results.append({"position":position,"decision_id":action["decision_id"],"status":"blocked","reason":"human_approval_required"})
                continue
            if self.execution_gate:
                gate = self.execution_gate.request(tenant_id, workspace_id, plan_id, action["action"],
                                                   risk=action.get("risk", "normal"), actor_id=str(approver_id or "system"))
                if gate["status"] != "approved":
                    results.append({"position":position,"decision_id":action["decision_id"],"status":"blocked","reason":gate["reason"],"execution_gate":gate})
                    continue
                gate_check = self.execution_gate.can_execute(tenant_id, workspace_id, plan_id, action["action"])
                if not gate_check["allowed"]:
                    results.append({"position":position,"decision_id":action["decision_id"],"status":"blocked","reason":gate_check["reason"],"execution_gate":gate_check})
                    continue
            if self.governance:
                governance_check = self.governance.check(
                    str(tenant_id), str(workspace_id), str(action.get("agent_id", "default")),
                    action.get("action", "unknown"), risk=action.get("risk", "read"),
                    steps=position, cost=action.get("cost", 0), tool=action.get("tool"),
                    approved=True if self.execution_gate and gate.get("status") == "approved" else False)
                if not governance_check["allowed"]:
                    results.append({"position":position,"decision_id":action["decision_id"],"status":"blocked","reason":governance_check["reason"],"governance":governance_check})
                    continue
            now=datetime.now(timezone.utc).isoformat()
            with self._db() as c:
                c.execute("""INSERT OR REPLACE INTO executions
                    (plan_id,position,tenant_id,workspace_id,decision_id,status,started_at,approval_id)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (plan_id,position,str(tenant_id),str(workspace_id),action["decision_id"],"running",now,approval["approval_id"]))
            self.events.publish("agent.plan.action.started",str(tenant_id),str(workspace_id),
                                actor_id=str(approver_id or "system"),entity_type="plan",entity_id=plan_id,reference_id=action["decision_id"],
                                payload={"position":position,"decision_id":action["decision_id"]})
            try:
                result=self.workflow.execute(str(tenant_id),str(workspace_id),action["decision_id"],
                    owner_id=owner_id,task=task,opportunity=opportunity,changed_by=changed_by)
                status="completed" if result.get("status") == "executed" or result.get("status") == "already_executed" else "failed"
                reason=result.get("reason","")
            except Exception as exc:
                result={"status":"failed","reason":str(exc)}; status="failed"
            finished=datetime.now(timezone.utc).isoformat()
            import json
            with self._db() as c:
                c.execute("UPDATE executions SET status=?,finished_at=?,result_json=? WHERE plan_id=? AND position=?",
                          (status,finished,json.dumps(result),plan_id,position))
            self.events.publish("agent.plan.action."+status,str(tenant_id),str(workspace_id),
                                actor_id=str(approver_id or "system"),entity_type="plan",entity_id=plan_id,reference_id=action["decision_id"],
                                payload={"position":position,"decision_id":action["decision_id"],"reason":reason})
            self.learning.record_action(str(tenant_id),str(workspace_id),"default",plan_id,position,action["action"],status,reason,action.get("context_fingerprint",""),action["decision_id"])
            results.append({"position":position,"decision_id":action["decision_id"],"status":status,"result":result})
        return {"plan_id":plan_id,"status":"completed" if results and all(x.get("status") in ("completed","already_executed") for x in results) else "partial","results":results}

    def feedback(self, tenant_id, workspace_id, plan_id):
        """Summarize execution outcomes without triggering new side effects."""
        plan = self.planner.get(tenant_id, workspace_id, plan_id)
        counts = {"completed": 0, "failed": 0, "blocked": 0, "pending": 0, "running": 0}
        with self._db() as c:
            rows = c.execute("SELECT position,status,result_json FROM executions WHERE tenant_id=? AND workspace_id=? AND plan_id=? ORDER BY position",
                             (str(tenant_id), str(workspace_id), str(plan_id))).fetchall()
        for row in rows:
            status = row["status"] if row["status"] in counts else "failed"
            counts[status] += 1
        total = len(plan["actions"])
        if total and counts["completed"] == total:
            outcome = "success"
        elif counts["failed"]:
            outcome = "failure"
        elif counts["blocked"] or counts["pending"] or counts["running"]:
            outcome = "incomplete"
        else:
            outcome = "not_started"
        return {"plan_id": plan_id, "outcome": outcome, "counts": counts, "action_count": total}

    def replan(self, tenant_id, workspace_id, plan_id, trigger="execution_feedback"):
        feedback = self.feedback(tenant_id, workspace_id, plan_id)
        if feedback["outcome"] == "success":
            return {"status": "no_replan", "reason": "plan_completed", "feedback": feedback}
        return {"status": "replan_required", "reason": feedback["outcome"], "feedback": feedback}
    def health(self):
        with self._db() as c:
            count=c.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
        return {"status":"ok","engine":"plan-executor","approval_required":True,
                "execution_separate_from_planning":True,"bounded":True,"max_actions":self.max_actions,
                "tenant_workspace_scoped":True,"executions":count}
