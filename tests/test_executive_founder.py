from src.core.executive_founder import ExecutiveFounder


def test_executive_health():
    e = ExecutiveFounder()
    assert e.health()["status"] == "ok"
    assert e.health()["credentials_exposed"] is False


def test_priority_and_decision_governance():
    e = ExecutiveFounder()
    priority = e.create_priority("Build enterprise platform", "Founder")
    blocked = e.activate_priority(priority["priority_id"])
    active = e.activate_priority(priority["priority_id"], approved=True)
    decision = e.create_decision("Architecture decision", ["A", "B"])
    decision_blocked = e.approve_decision(decision["decision_id"])
    decision_ok = e.approve_decision(decision["decision_id"], approved=True)
    assert blocked["allowed"] is False
    assert active["status"] == "active"
    assert decision_blocked["allowed"] is False
    assert decision_ok["status"] == "approved"


def test_board_brief_and_snapshot():
    e = ExecutiveFounder()
    board = e.create_board_matter("Quarterly strategy", "portfolio data")
    brief = e.create_brief("Executive Brief", "Current position and risks", 0.92)
    snapshot = e.portfolio_snapshot({"projects": 12, "risk": "medium"})
    assert board["status"] == "draft"
    assert brief["confidence"] == 0.92
    assert snapshot["stale_data_flag"] is False
