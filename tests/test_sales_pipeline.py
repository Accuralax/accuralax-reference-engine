from src.core.sales_pipeline import SalesPipeline, STAGES

def test_sales_pipeline_lifecycle(tmp_path):
    e = SalesPipeline(str(tmp_path / "sales.sqlite3"))
    lead = e.create_lead("t1", "w1", "CLI-1", "website", score=80)
    assert lead["status"] == "new_enquiry"
    e.assign_owner("t1", "w1", lead["lead_id"], "owner-1")
    e.move_stage("t1", "w1", lead["lead_id"], "qualified", "owner-1", "validated")
    e.move_stage("t1", "w1", lead["lead_id"], "proposal", "owner-1", "proposal_sent")
    assert e.get_lead("t1", "w1", lead["lead_id"])["owner_id"] == "owner-1"
    assert [x["to_stage"] for x in e.history("t1", "w1", lead["lead_id"])] == ["new_enquiry", "qualified", "proposal"]

def test_sales_pipeline_is_scoped(tmp_path):
    e = SalesPipeline(str(tmp_path / "sales.sqlite3"))
    lead = e.create_lead("t1", "w1", "CLI-1")
    assert e.get_lead("t2", "w1", lead["lead_id"]) is None
    assert e.pipeline("t2", "w1")["total_leads"] == 0

def test_sales_pipeline_validates_stage_and_client(tmp_path):
    e = SalesPipeline(str(tmp_path / "sales.sqlite3"))
    try:
        e.create_lead("t1", "w1", "")
        assert False
    except ValueError as exc:
        assert str(exc) == "client_id_required"
    lead = e.create_lead("t1", "w1", "CLI-2")
    try:
        e.move_stage("t1", "w1", lead["lead_id"], "bad_stage")
        assert False
    except ValueError as exc:
        assert str(exc) == "invalid_stage"
    assert set(STAGES) == {"new_enquiry", "qualified", "discovery", "proposal", "negotiation", "won", "lost"}

def test_sales_pipeline_dashboard_counts(tmp_path):
    e = SalesPipeline(str(tmp_path / "sales.sqlite3"))
    a = e.create_lead("t1", "w1", "CLI-1")
    b = e.create_lead("t1", "w1", "CLI-2")
    e.move_stage("t1", "w1", a["lead_id"], "qualified")
    e.move_stage("t1", "w1", b["lead_id"], "won")
    view = e.pipeline("t1", "w1")
    assert view["total_leads"] == 2
    assert view["stages"]["qualified"]["count"] == 1
    assert view["stages"]["won"]["count"] == 1
