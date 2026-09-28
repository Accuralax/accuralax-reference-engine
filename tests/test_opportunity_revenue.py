from src.core.opportunity_revenue import OpportunityRevenue

def test_opportunity_lifecycle_and_revenue(tmp_path):
    e = OpportunityRevenue(str(tmp_path / "opp.sqlite3"))
    opp = e.create("t1", "w1", "CLI-1", "Website build", 10000, "ZAR", 60, "2026-12-31", "LED-1")
    assert opp["status"] == "open"
    e.update_stage("t1", "w1", opp["opportunity_id"], "proposal", "owner-1", "proposal_sent")
    won = e.close("t1", "w1", opp["opportunity_id"], "won", "owner-1", "contract_signed")
    assert won["status"] == "won"
    assert won["stage"] == "closed_won"
    report = e.revenue("t1", "w1", "ZAR")
    assert report["won_revenue"] == 10000
    assert report["total_opportunities"] == 1
    assert len(e.history("t1", "w1", opp["opportunity_id"])) == 3

def test_opportunity_validation_and_scope(tmp_path):
    e = OpportunityRevenue(str(tmp_path / "opp.sqlite3"))
    try:
        e.create("t1", "w1", "", "x")
        assert False
    except ValueError as exc:
        assert str(exc) == "client_id_required"
    try:
        e.create("t1", "w1", "CLI-1", "x", 100, "ZAR", 101)
        assert False
    except ValueError as exc:
        assert str(exc) == "probability_out_of_range"
    opp = e.create("t1", "w1", "CLI-1", "x", 100, "ZAR")
    assert e.get("t2", "w1", opp["opportunity_id"]) is None
    try:
        e.close("t1", "w1", opp["opportunity_id"], "lost")
        assert False
    except ValueError as exc:
        assert str(exc) == "lost_reason_required"
