from src.core.agent_workflow import AgentWorkflow
from src.core.sales_pipeline import SalesPipeline
from src.core.followup_tasks import FollowUpTasks
from src.core.opportunity_revenue import OpportunityRevenue

def test_workflow_decisions(tmp_path):
    e = AgentWorkflow(str(tmp_path / "workflow.sqlite3"))
    lead = {"lead_id": "LED-1", "status": "qualified", "score": 85, "owner_id": None}
    result = e.decide("t1", "w1", "CLI-1", lead=lead, consent_granted=False, open_tasks=0)
    actions = {x["action"] for x in result["next_actions"]}
    assert {"assign_owner", "request_consent", "create_opportunity"} <= actions
    did = result["next_actions"][0]["decision_id"]
    assert e.mark_executed("t1", "w1", did)["executed"] is True

def test_workflow_consent_changes_followup(tmp_path):
    e = AgentWorkflow(str(tmp_path / "workflow.sqlite3"))
    lead = {"lead_id": "LED-2", "status": "new", "score": 20, "owner_id": "owner-1"}
    result = e.decide("t1", "w1", "CLI-2", lead=lead, consent_granted=True, open_tasks=0)
    actions = {x["action"] for x in result["next_actions"]}
    assert "request_consent" not in actions
    assert "create_followup" in actions
    assert len(e.history("t1", "w1", "CLI-2")) == 1

def test_execution_creates_followup_and_customer_scope(tmp_path):
    tasks = FollowUpTasks(str(tmp_path / "tasks.sqlite3"))
    e = AgentWorkflow(str(tmp_path / "workflow.sqlite3"), followup_tasks=tasks)
    lead = {"lead_id": "LED-3", "status": "qualified", "score": 60, "owner_id": "owner-1"}
    result = e.decide("t1", "w1", "CLI-3", lead=lead, consent_granted=True, open_tasks=0)
    decision = next(x for x in result["next_actions"] if x["action"] == "create_followup")
    executed = e.execute("t1", "w1", decision["decision_id"], task={"title": "Call client"})
    assert executed["status"] == "executed"
    assert executed["result"]["title"] == "Call client"

def test_execution_creates_opportunity(tmp_path):
    opps = OpportunityRevenue(str(tmp_path / "opps.sqlite3"))
    e = AgentWorkflow(str(tmp_path / "workflow.sqlite3"), opportunities=opps)
    lead = {"lead_id": "LED-4", "status": "qualified", "score": 90, "owner_id": "owner-1"}
    result = e.decide("t1", "w1", "CLI-4", lead=lead, consent_granted=True, open_tasks=1)
    decision = next(x for x in result["next_actions"] if x["action"] == "create_opportunity")
    executed = e.execute("t1", "w1", decision["decision_id"], opportunity={"name": "Enterprise package", "value": 10000, "currency": "ZAR", "probability": 50})
    assert executed["status"] == "executed"
    assert executed["result"]["status"] == "open"
