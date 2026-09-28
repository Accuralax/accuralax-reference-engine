from src.core.compliance_engine import ComplianceEngine

def test_compliance_engine_detects_gaps_and_risk():
    result = ComplianceEngine().assess([
        {"control_id": "TAX-001", "domain": "tax", "requirement": "Return filed",
         "owner": "Finance", "status": "non_compliant", "evidence": None,
         "source": "internal", "confidence": "low", "impact": "high",
         "remediation": "File outstanding return"}
    ])
    assert result["control_count"] == 1
    assert len(result["gap_report"]) == 1
    assert len(result["evidence_gaps"]) == 1
    assert result["risk_report"][0]["risk"]["level"] == "high"
    assert result["requires_human_review"] is True

def test_compliant_without_evidence_is_not_claimed_as_compliant():
    result = ComplianceEngine().assess([
        {"control_id": "SEC-001", "status": "compliant", "evidence": None}
    ])
    assert result["compliance_matrix"][0]["status"] == "unknown"
    assert result["compliance_matrix"][0]["evidence_gap"] is True
