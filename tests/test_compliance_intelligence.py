from src.core.compliance_intelligence import ComplianceIntelligence
from src.core.compliance_risk_engine import ComplianceRiskEngine

def test_gap_detection_and_summary(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "compliance.sqlite3"))
    intel = ComplianceIntelligence(engine)
    obligation = engine.add_obligation("t1", "w1", "Annual filing")
    risk = engine.assess_risk("t1", "w1", "Late filing", 5, 5, obligation["obligation_id"])
    gaps = intel.gaps("t1", "w1")
    assert any(x["type"] == "missing_control" for x in gaps)
    assert any(x["type"] == "missing_evidence" for x in gaps)
    assert any(x["type"] == "unremediated_risk" for x in gaps)
    summary = intel.summary("t1", "w1")
    assert summary["obligations"] == 1
    assert summary["risks"] == 1
    assert summary["gaps"] >= 3

def test_gap_detection_is_scope_isolated(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "compliance.sqlite3"))
    intel = ComplianceIntelligence(engine)
    engine.add_obligation("t1", "w1", "Requirement A")
    engine.add_obligation("t2", "w2", "Requirement B")
    assert intel.summary("t1", "w1")["obligations"] == 1
    assert intel.summary("t2", "w2")["obligations"] == 1

def test_recommendations_are_actionable(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "compliance.sqlite3"))
    intel = ComplianceIntelligence(engine)
    engine.add_obligation("t1", "w1", "Requirement")
    recommendations = intel.recommendations("t1", "w1")
    assert recommendations
    assert recommendations[0]["recommendation"]
