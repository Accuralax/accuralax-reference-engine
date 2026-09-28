from src.core.compliance_risk_engine import ComplianceRiskEngine
from src.core.compliance_intelligence import ComplianceIntelligence
from src.core.compliance_report_agent import ComplianceReportAgent

def test_report_is_reviewable(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    intelligence = ComplianceIntelligence(engine)
    agent = ComplianceReportAgent(intelligence, str(tmp_path / "reports.sqlite3"))
    engine.add_obligation("t1", "w1", "Annual filing")
    report = agent.generate("t1", "w1", generated_by="agent-1")
    assert report["assurance"]["evidence_backed"] is True
    assert report["assurance"]["human_review_required"] is True
    assert report["assurance"]["legal_conclusion"] is False
    reviewed = agent.review("t1", "w1", report["report_id"], "reviewer-1", True)
    assert reviewed["status"] == "approved"

def test_report_scope_isolation(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    intelligence = ComplianceIntelligence(engine)
    agent = ComplianceReportAgent(intelligence, str(tmp_path / "reports.sqlite3"))
    report = agent.generate("t1", "w1")
    assert agent.get("t2", "w2", report["report_id"]) is None
    assert agent.recent("t1", "w1")[0]["report_id"] == report["report_id"]
