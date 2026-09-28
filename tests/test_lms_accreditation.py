import tempfile
from src.core.lms_accreditation import LMSAccreditation


def engine():
    return LMSAccreditation(db_path=tempfile.mktemp(suffix=".sqlite3"))


def test_qualification_accreditation_and_mapping():
    a=engine()
    q=a.register_qualification("t","w","Robotics Certificate",code="ROB-01",authority="QCTO",nqf_level="4",credits=28)
    assert q["status"] == "draft"
    a.add_requirement("t","w",q["qualification_id"],"attendance","Attendance",80,"percent",True,"attendance")
    a.map_programme("t","w",q["qualification_id"],"PROG-1",95,"active")
    app=a.submit_accreditation("t","w",q["qualification_id"],"QCTO","REF-1")
    out=a.decide_accreditation("t","w",app["application_id"],"approved","reviewer")
    assert out["status"] == "approved"
    assert a.get_qualification("t","w",q["qualification_id"])["status"] == "active"


def test_portfolio_evidence_and_eligibility():
    a=engine()
    q=a.register_qualification("t","w","ICT Certificate")["qualification_id"]
    req=a.add_requirement("t","w",q,"evidence","Project evidence",evidence_type="project")
    p=a.create_portfolio("t","w","L1",q)
    e=a.add_evidence("t","w",p["portfolio_id"],"project","Final project",requirement_id=req["requirement_id"])
    assert a.eligibility("t","w","L1",q)["eligible"] is False
    a.verify_evidence("t","w",e["evidence_id"],True,"assessor")
    assert a.eligibility("t","w","L1",q)["eligible"] is True


def test_moderation_and_certificate_verification():
    a=engine()
    m=a.moderate_assessment("t","w",learner_id="L1",assessment_id="A1",assessor_id="AS1")
    out=a.decide_moderation("t","w",m["moderation_id"],"approved","MOD1","sample accepted")
    assert out["status"] == "approved"
    a.register_certificate("t","w","L1","Q1","CERT-001","hash")
    assert a.verify_certificate("t","w","CERT-001")["valid"] is True
    assert a.revoke_certificate("t","w","CERT-001","administrative review")["valid"] is False


def test_portfolio_submission_preserves_unverified_count():
    a=engine()
    q=a.register_qualification("t","w","Data Certificate")["qualification_id"]
    p=a.create_portfolio("t","w","L2",q)
    a.add_evidence("t","w",p["portfolio_id"],"document","Identity evidence")
    result=a.submit_portfolio("t","w",p["portfolio_id"])
    assert result["status"] == "submitted"
    assert result["unverified_evidence"] == 1


def test_tenant_isolation_for_certificate():
    a=engine()
    a.register_certificate("t1","w1","L1","Q1","CERT-X")
    assert a.verify_certificate("t2","w2","CERT-X")["valid"] is False
