import os
import tempfile
import unittest

from src.core.agent_workflow import AgentWorkflow
from src.core.agent_planner import AgentPlanner
from src.core.human_approval import HumanApprovalGateway
from src.core.plan_executor import PlanExecutor

class FakeWorkflow:
    def __init__(self):
        self.calls=[]
    def execute(self, tenant_id, workspace_id, decision_id, **kwargs):
        self.calls.append((tenant_id,workspace_id,decision_id,kwargs))
        return {"status":"executed","decision_id":decision_id}

class PlannerStub:
    def __init__(self, actions):
        self.actions=actions
    def get(self, tenant_id, workspace_id, plan_id):
        return {"plan":{"plan_id":plan_id,"status":"proposed"},"actions":self.actions}

class TestPlanExecutor(unittest.TestCase):
    def test_blocks_without_approval_and_executes_after_approval(self):
        with tempfile.TemporaryDirectory() as td:
            approvals=HumanApprovalGateway(os.path.join(td,"approvals.sqlite3"))
            workflow=FakeWorkflow()
            actions=[{"decision_id":"DEC-1","action":"assign_owner","reason":"owner missing"}]
            planner=PlannerStub(actions)
            executor=PlanExecutor(planner,workflow,approvals,os.path.join(td,"exec.sqlite3"))
            blocked=executor.execute("t1","w1","PLN-1")
            self.assertEqual(blocked["results"][0]["status"],"blocked")
            self.assertEqual(len(workflow.calls),0)
            approval=executor.request_approval("t1","w1","PLN-1",1,"user1")
            self.assertEqual(approval["status"],"requested")
            approvals.approve("t1","w1",approval["approval_id"],"approver1")
            done=executor.execute("t1","w1","PLN-1",approver_id="approver1")
            self.assertEqual(done["results"][0]["status"],"completed")
            self.assertEqual(len(workflow.calls),1)
    def test_approval_is_scope_bound(self):
        with tempfile.TemporaryDirectory() as td:
            approvals=HumanApprovalGateway(os.path.join(td,"approvals.sqlite3"))
            a=approvals.request("t1","w1","p1",1,"d1","u")
            with self.assertRaises(ValueError):
                approvals.get("t2","w1",a["approval_id"])
            with self.assertRaises(ValueError):
                approvals.approve("t2","w1",a["approval_id"],"admin")

    def test_rejection_blocks_execution(self):
        with tempfile.TemporaryDirectory() as td:
            approvals=HumanApprovalGateway(os.path.join(td,"approvals.sqlite3"))
            workflow=FakeWorkflow()
            planner=PlannerStub([{"decision_id":"d1","action":"assign_owner","reason":"x"}])
            executor=PlanExecutor(planner,workflow,approvals,os.path.join(td,"exec.sqlite3"))
            a=executor.request_approval("t","w","p",1,"u")
            approvals.reject("t","w",a["approval_id"],"admin","not allowed")
            result=executor.execute("t","w","p")
            self.assertEqual(result["results"][0]["status"],"blocked")
            self.assertEqual(len(workflow.calls),0)

    def test_duplicate_execution_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            approvals=HumanApprovalGateway(os.path.join(td,"approvals.sqlite3"))
            workflow=FakeWorkflow()
            planner=PlannerStub([{"decision_id":"d1","action":"assign_owner","reason":"x"}])
            executor=PlanExecutor(planner,workflow,approvals,os.path.join(td,"exec.sqlite3"))
            a=executor.request_approval("t","w","p",1,"u")
            approvals.approve("t","w",a["approval_id"],"admin")
            executor.execute("t","w","p")
            executor.execute("t","w","p")
            self.assertEqual(len(workflow.calls),1)

    def test_workflow_decisions_remain_separate_from_approval(self):
        with tempfile.TemporaryDirectory() as td:
            wf=AgentWorkflow(os.path.join(td,"workflow.sqlite3"))
            planner=AgentPlanner(wf,os.path.join(td,"planner.sqlite3"),max_actions=1)
            plan=planner.plan("t","w","client",lead={"lead_id":"l1","status":"new","score":10},consent_granted=False)
            self.assertEqual(plan["status"],"proposed")
            self.assertEqual(plan["action_budget"],1)
            self.assertEqual(plan["actions"][0]["action"],"assign_owner")

if __name__ == "__main__":
    unittest.main()
