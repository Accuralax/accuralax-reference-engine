from src.core.payments_financial import PaymentsFinancial


def test_finance_health():
    f = PaymentsFinancial()
    assert f.health()["status"] == "ok"
    assert f.health()["credentials_exposed"] is False


def test_payment_refund_and_reconciliation():
    f = PaymentsFinancial()
    account = f.create_account("Customer")
    invoice = f.create_invoice("CUS-1", 2500)
    blocked = f.request_payment(invoice["invoice_id"], 1000)
    payment = f.request_payment(invoice["invoice_id"], 1000, approved=True)
    refund_blocked = f.request_refund(payment["payment_id"], 250)
    refund = f.request_refund(payment["payment_id"], 250, approved=True)
    ledger = f.post_ledger("cash", "receivable", 1000)
    reconciliation = f.reconcile(payment["payment_id"], ledger["ledger_id"])
    assert account["currency"] == "ZAR"
    assert blocked["allowed"] is False
    assert payment["status"] == "captured"
    assert refund_blocked["allowed"] is False
    assert refund["status"] == "processed"
    assert reconciliation["status"] == "matched"


def test_budget_requires_approval():
    f = PaymentsFinancial()
    blocked = f.set_budget("Technology", 10000)
    budget = f.set_budget("Technology", 10000, approved=True)
    assert blocked["allowed"] is False
    assert budget["status"] == "approved"
