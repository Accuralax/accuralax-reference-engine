from pathlib import Path
from src.core.customer_360 import Customer360
from src.core.opportunity_revenue import OpportunityRevenue
from src.core.followup_tasks import FollowUpTasks


def test_sales_components_emit_domain_events(tmp_path: Path):
    c360 = Customer360(str(tmp_path / "c360.sqlite3"))
    c360.add_relationship("t1", "w1", "C1", "decision_maker", "Owner")
    c360.set_consent("t1", "w1", "C1", "outreach", True)
    c360.record_event("t1", "w1", "C1", "whatsapp", "message", "Hello")
    assert len(c360.events.history("t1", "w1", entity_id="C1")) == 3

    opp = OpportunityRevenue(str(tmp_path / "opp.sqlite3"))
    item = opp.create("t1", "w1", "C1", "Website", value=1000, currency="ZAR")
    opp.update_stage("t1", "w1", item["opportunity_id"], "proposal")
    opp.close("t1", "w1", item["opportunity_id"], "won")
    assert len(opp.events.history("t1", "w1", entity_id=item["opportunity_id"])) == 3

    tasks = FollowUpTasks(str(tmp_path / "tasks.sqlite3"))
    task = tasks.create("t1", "w1", "C1", "Call client")
    tasks.update_status("t1", "w1", task["task_id"], "completed")
    assert len(tasks.events.history("t1", "w1", entity_id=task["task_id"])) == 2
