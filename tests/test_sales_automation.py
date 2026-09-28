from src.core.sales_automation import SalesAutomation
from src.core.sales_pipeline import SalesPipeline
from src.core.opportunity_revenue import OpportunityRevenue
from src.core.customer_360 import Customer360

def test_sales_automation_intake_and_consent(tmp_path):
    pipeline = SalesPipeline(str(tmp_path / "pipeline.sqlite3"))
    opps = OpportunityRevenue(str(tmp_path / "opps.sqlite3"))
    c360 = Customer360(str(tmp_path / "c360.sqlite3"))
    e = SalesAutomation(str(tmp_path / "automation.sqlite3"), pipeline, opps, c360)
    result = e.intake("t1", "w1", "CLI-1", "website", 85, "owner-1", "Website enquiry", "needs site", False)
    assert result["lead"]["client_id"] == "CLI-1"
    assert result["outreach_allowed"] is False
    consent = e.authorize_outreach("t1", "w1", "CLI-1", True)
    assert consent["granted"] is True
    assert e.outreach_gate("t1", "w1", "CLI-1")["allowed"] is True
    assert len(e.history("t1", "w1", "CLI-1")) == 2

def test_sales_automation_opportunity_audit(tmp_path):
    pipeline = SalesPipeline(str(tmp_path / "pipeline.sqlite3"))
    opps = OpportunityRevenue(str(tmp_path / "opps.sqlite3"))
    c360 = Customer360(str(tmp_path / "c360.sqlite3"))
    e = SalesAutomation(str(tmp_path / "automation.sqlite3"), pipeline, opps, c360)
    opp = e.create_opportunity("t1", "w1", "CLI-9", "Consulting", 5000, "ZAR", 50, lead_id="LED-9")
    assert opp["lead_id"] == "LED-9"
    assert e.history("t1", "w1", "CLI-9")[0]["action"] == "opportunity_creation"
