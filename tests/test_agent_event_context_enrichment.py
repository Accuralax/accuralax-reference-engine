import tempfile
from pathlib import Path
from src.core.agent_planner import AgentPlanner
from src.core.agent_workflow import AgentWorkflow
from src.core.sales_pipeline import SalesPipeline
from src.core.opportunity_revenue import OpportunityRevenue
from src.core.event_bus import DomainEvent


def test_lead_event_resolves_authoritative_lead():
    with tempfile.TemporaryDirectory() as d:
        p=SalesPipeline(str(Path(d)/"sales.sqlite3")); o=OpportunityRevenue(str(Path(d)/"opp.sqlite3"))
        w=AgentWorkflow(str(Path(d)/"workflow.sqlite3"),pipeline=p,opportunities=o)
        planner=AgentPlanner(w,db_path=str(Path(d)/"planner.sqlite3"))
        lead=p.create_lead("t","w","cli-1","Lead One",80)
        event=DomainEvent("e1","sales.lead.created","t","w","a","lead",lead["lead_id"],None,{"client_id":"cli-1"},"2026-01-01T00:00:00+00:00")
        result=planner.process_event(event,consent_granted=True)
        assert any(a["action"] == "create_opportunity" for a in result["actions"])

def test_opportunity_event_resolves_authoritative_opportunity():
    with tempfile.TemporaryDirectory() as d:
        p=SalesPipeline(str(Path(d)/"sales.sqlite3")); o=OpportunityRevenue(str(Path(d)/"opp.sqlite3"))
        w=AgentWorkflow(str(Path(d)/"workflow.sqlite3"),pipeline=p,opportunities=o)
        planner=AgentPlanner(w,db_path=str(Path(d)/"planner.sqlite3"))
        opp=o.create("t","w","cli-2","Deal",1000,"ZAR",50,None,None)
        event=DomainEvent("e2","sales.opportunity.created","t","w","a","opportunity",opp["opportunity_id"],None,{"client_id":"cli-2"},"2026-01-01T00:00:00+00:00")
        result=planner.process_event(event,lead={"status":"proposal","score":80},consent_granted=True)
        assert result["plan_id"].startswith("PLN-")
