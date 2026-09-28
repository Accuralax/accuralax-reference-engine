from src.core.compliance_risk_report import ComplianceRiskReportAgent, ComplianceControl


def test_compliance_matrix_and_gap_detection():
    agent = ComplianceRiskReportAgent()
    result = agent.add_control(ComplianceControl(
        "TAX-001", "tax", "Returns filed", "finance",
        status="partial", evidence="", source="internal-review", remediation="Complete filing"
    ))
    assert result["allowed"]
    gaps = agent.gaps()
    assert gaps[0]["control_id"] == "TAX-001"
    assert gaps[0]["evidence_gap"]


def test_risk_matrix():
    agent = ComplianceRiskReportAgent()
    risk = agent.assess_risk("R-001", 4, 5, "Regulatory exposure")
    assert risk["allowed"]
    assert risk["score"] == 20
    assert risk["level"] == "critical"


def test_report_generator_is_provenance_and_secret_safe():
    agent = ComplianceRiskReportAgent()
    agent.add_control(ComplianceControl(
        "SEC-001", "information_security", "Access control", "IT",
        status="compliant", evidence="review-1", source="audit"
    ))
    report = agent.generate_report()
    assert report["generated_content"]
    assert report["content_hash"]
    assert report["credentials_exposed"] is False
    assert "api_key" not in str(report)
