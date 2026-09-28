from src.core.compliance_risk_engine import ComplianceRiskEngine


def test_matrix_v2_builds_full_traceability(tmp_path):
    e = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    o = e.add_obligation("t1", "w1", "Annual filing")
    c = e.add_control("t1", "w1", o["obligation_id"], "Review filing")
    r = e.assess_risk("t1", "w1", "Late filing", 4, 4, o["obligation_id"])
    a = e.add_action("t1", "w1", "Submit correction", r["risk_id"], o["obligation_id"])
    ev = e.add_evidence("t1", "w1", "Signed receipt")
    e.link_evidence("t1", "w1", ev["evidence_id"], o["obligation_id"], c["control_id"])
    matrix = e.matrix_v2("t1", "w1")
    row = matrix["rows"][0]
    assert row["control_coverage"] is True
    assert row["evidence_coverage"] is True
    assert row["verified_evidence_coverage"] is False
    assert row["actions"][0]["action_id"] == a["action_id"]


def test_matrix_v2_status_lifecycle(tmp_path):
    e = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    o = e.add_obligation("t1", "w1", "Requirement")
    c = e.add_control("t1", "w1", o["obligation_id"], "Control")
    r = e.assess_risk("t1", "w1", "Risk", 3, 3, o["obligation_id"])
    assert e.update_obligation_status("t1", "w1", o["obligation_id"], "in_progress")["status"] == "in_progress"
    assert e.update_control_status("t1", "w1", c["control_id"], "effective")["status"] == "effective"
    assert e.update_risk_status("t1", "w1", r["risk_id"], "mitigated")["status"] == "mitigated"


def test_matrix_v2_rejects_cross_tenant_links(tmp_path):
    e = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    o1 = e.add_obligation("t1", "w1", "Private")
    ev2 = e.add_evidence("t2", "w2", "Other")
    try:
        e.link_evidence("t1", "w1", ev2["evidence_id"], o1["obligation_id"])
        assert False
    except ValueError as exc:
        assert str(exc) == "evidence_not_found"


def test_matrix_v2_health(tmp_path):
    e = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    health = e.health()
    assert health["matrix_v2"] is True
    assert health["traceability"] is True
