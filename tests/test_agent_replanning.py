import os
import tempfile
import unittest
from src.core.agent_replanning import AgentReplanningEngine

class ExecutorStub:
    def __init__(self, outcome): self.outcome=outcome
    def feedback(self, tenant, workspace, plan):
        return {"plan_id":plan,"outcome":self.outcome,"counts":{},"action_count":1}

class PlannerStub:
    def __init__(self): self.calls=0
    def plan(self,*args,**kwargs):
        self.calls += 1
        return {"plan_id":"PLN-NEW","status":"proposed","actions":[]}

class TestReplanning(unittest.TestCase):
    def test_failure_creates_proposed_plan(self):
        with tempfile.TemporaryDirectory() as td:
            p=PlannerStub(); e=AgentReplanningEngine(p,ExecutorStub("failure"),os.path.join(td,"r.sqlite3"))
            result=e.propose("t","w","PLN-1",lead={"client_id":"c1"})
            self.assertEqual(result["status"],"proposed")
            self.assertEqual(result["reason"],"execution_failure")
            self.assertEqual(p.calls,1)

    def test_completed_plan_is_not_replanned(self):
        with tempfile.TemporaryDirectory() as td:
            p=PlannerStub(); e=AgentReplanningEngine(p,ExecutorStub("success"),os.path.join(td,"r.sqlite3"))
            result=e.propose("t","w","PLN-1")
            self.assertEqual(result["status"],"no_replan")
            self.assertEqual(p.calls,0)

    def test_replan_budget_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            p=PlannerStub(); e=AgentReplanningEngine(p,ExecutorStub("failure"),os.path.join(td,"r.sqlite3"),max_replans=1)
            e.propose("t","w","PLN-1")
            second=e.propose("t","w","PLN-1")
            self.assertEqual(second["status"],"blocked")
            self.assertEqual(p.calls,1)

    def test_scope_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            p=PlannerStub(); e=AgentReplanningEngine(p,ExecutorStub("failure"),os.path.join(td,"r.sqlite3"))
            result=e.propose("t1","w1","PLN-1")
            with self.assertRaises(ValueError): e.get("t2","w1",result["replan_id"])

if __name__ == "__main__": unittest.main()
