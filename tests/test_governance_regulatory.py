from src.core.governance_regulatory import GovernanceRegulatory


def test_governance_health():
    g = GovernanceRegulatory()
    assert g.health()["status"] == "ok"
    assert g.health()["credentials_exposed"] is False


def test_policy_and_regulation_controls():
    g = GovernanceRegulatory()
    policy = g.register_policy("Information Security Policy", "CISO", "internal")
    blocked = g.approve_policy(policy["policy_id"])
    approved = g.approve_policy(policy["policy_id"], approved=True)
    regulation = g.register_regulation("Data Protection Requirement", "Authority", "2026-01-01")
    obligation = g.create_obligation(regulation["regulation_id"], "Compliance", "Protect personal data")
    assessment = g.assess_compliance(obligation["obligation_id"], "compliant", "audit evidence")
    evidence = g.record_evidence(assessment["assessment_id"], "audit", "EV-001")
    assert blocked["allowed"] is False
    assert approved["status"] == "approved"
    assert obligation["status"] == "assigned"
    assert assessment["status"] == "compliant"
    assert evidence["reference"] == "EV-001"


def test_policy_exception_requires_human_review():
    g = GovernanceRegulatory()
    blocked = g.request_exception("retention", "business need")
    assert blocked["allowed"] is False
    assert blocked["policy"]["outcome"] == "awaiting_human_review"
