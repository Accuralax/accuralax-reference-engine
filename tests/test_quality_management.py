from src.core.quality_management import QualityManagement


def test_quality_health():
    q = QualityManagement()
    assert q.health()["status"] == "ok"
    assert q.health()["credentials_exposed"] is False


def test_inspection_finding_and_capa():
    q = QualityManagement()
    standard = q.create_standard("CyberFusion Quality Standard", "1.0")
    assert standard["status"] == "active"

    missing = q.record_inspection("OFF-1", "fail", "")
    assert missing["allowed"] is False
    inspection = q.record_inspection("OFF-1", "fail", "inspection evidence")
    finding = q.create_finding(inspection["inspection_id"], "high", "Control failure")
    assert finding["status"] == "open"

    blocked = q.create_capa(finding["finding_id"], "owner", "Correct control")
    assert blocked["allowed"] is False
    capa = q.create_capa(finding["finding_id"], "owner", "Correct control", approved=True)
    assert capa["status"] == "approved"

    verify = q.verify_capa(capa["capa_id"], True, approved=True)
    assert verify["status"] == "closed"


def test_audit_and_metric():
    q = QualityManagement()
    audit = q.create_audit("Supplier quality")
    metric = q.register_metric("defect_rate", 0.02, "Defects divided by units")
    assert audit["status"] == "planned"
    assert metric["definition"] == "Defects divided by units"
