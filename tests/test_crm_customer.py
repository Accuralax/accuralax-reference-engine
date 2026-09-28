from src.core.crm_customer import CRMCustomer


def test_crm_health():
    assert CRMCustomer().health()["status"] == "ok"


def test_contact_duplicate_is_blocked():
    crm = CRMCustomer()
    crm.create_contact("A", "a@example.com", "Startup")
    try:
        crm.create_contact("B", "A@EXAMPLE.COM", "Startup")
        assert False
    except ValueError:
        assert True


def test_consent_and_handoff():
    crm = CRMCustomer()
    contact = crm.create_contact("A", "a@example.com", "Startup")
    assert crm.handoff(contact["contact_id"], "sales", False)["allowed"] is False
    crm.record_consent(contact["contact_id"], "marketing", True)
    assert crm.handoff(contact["contact_id"], "sales", True)["allowed"] is True


def test_lead_scoring():
    crm = CRMCustomer()
    contact = crm.create_contact("A", "a@example.com", "Business")
    lead = crm.create_lead(contact["contact_id"], {"fit":20,"intent":20,"engagement":20,"urgency":10,"completeness":15})
    assert lead["label"] == "high"
