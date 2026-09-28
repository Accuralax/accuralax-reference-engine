from src.core.finance_governance import GovernedFinance


def test_finance_governance_health():
    system = GovernedFinance()
    assert system.health()["status"] == "ok"


def test_payment_requires_governance_approval():
    system = GovernedFinance()
    invoice = system.finance.create_invoice("CUS-1", "1250.00", "INV-TEST-1")
    result = system.request_payment("founder", invoice["invoice_id"], "1250.00")
    assert result["allowed"] is False
    assert result["stage"] == "policy"


def test_approved_payment_is_lineaged():
    system = GovernedFinance()
    invoice = system.finance.create_invoice("CUS-2", "500.00", "INV-TEST-2")
    result = system.request_payment("founder", invoice["invoice_id"], "500.00", approved=True)
    assert result["allowed"] is True
    assert result["payment"]["state"] == "authorized"
    assert result["lineage"]["event_count"] == 1


def test_operator_cannot_use_finance_execute_scope():
    system = GovernedFinance()
    invoice = system.finance.create_invoice("CUS-3", "100.00", "INV-TEST-3")
    result = system.request_payment("operator", invoice["invoice_id"], "100.00", approved=True)
    assert result["allowed"] is False
    assert result["stage"] == "identity"
