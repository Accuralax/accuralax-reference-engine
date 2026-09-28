from src.core.compliance_risk_engine import ComplianceRiskEngine

def test_compliance_matrix_is_scoped_and_tracks_risk(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "compliance.sqlite3"))
    obligation = engine.add_obligation("t1","w1","Annual statutory filing","ZA","Authority","official-source")
    control = engine.add_control("t1","w1",obligation["obligation_id"],"Filing review")
    risk = engine.assess_risk("t1","w1","Late filing",4,4,obligation["obligation_id"])
    evidence = engine.add_evidence("t1","w1","Signed filing receipt","ref-1",obligation["obligation_id"],control["control_id"])
    verified = engine.verify_evidence("t1","w1",evidence["evidence_id"],"reviewer")
    action = engine.add_action("t1","w1","Submit corrective filing",risk["risk_id"],obligation["obligation_id"])
    matrix = engine.matrix("t1","w1")
    assert risk["level"] == "high"
    assert verified["verified"] == 1
    assert len(matrix["obligations"]) == 1
    assert len(matrix["risks"]) == 1
    assert len(matrix["actions"]) == 1

def test_compliance_scope_isolation(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "compliance.sqlite3"))
    engine.add_obligation("t1","w1","Requirement")
    engine.add_obligation("t2","w2","Other requirement")
    assert len(engine.matrix("t1","w1")["obligations"]) == 1
    assert len(engine.matrix("t2","w2")["obligations"]) == 1
