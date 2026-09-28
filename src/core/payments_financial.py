from __future__ import annotations

from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class PaymentsFinancial:
    """Governed billing, payments, ledger and reconciliation intelligence."""

    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, Any]] = {}
        self.invoices: dict[str, dict[str, Any]] = {}
        self.payments: dict[str, dict[str, Any]] = {}
        self.refunds: dict[str, dict[str, Any]] = {}
        self.ledger: list[dict[str, Any]] = []
        self.reconciliations: list[dict[str, Any]] = []
        self.budgets: dict[str, dict[str, Any]] = {}
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_account(self, owner: str, currency: str = "ZAR") -> dict[str, Any]:
        item = {"account_id": f"ACC-{uuid.uuid4().hex[:10].upper()}",
                "owner": owner, "currency": currency, "status": "active"}
        self.accounts[item["account_id"]] = item
        return self._safe(item)

    def create_invoice(self, customer_id: str, amount: float) -> dict[str, Any]:
        if amount <= 0:
            return {"allowed": False, "reason": "amount_must_be_positive"}
        item = {"invoice_id": f"INV-{uuid.uuid4().hex[:10].upper()}",
                "customer_id": customer_id, "amount": amount, "status": "issued"}
        self.invoices[item["invoice_id"]] = item
        self.lineage.record("invoice.created", "finance", "invoice",
                            item["invoice_id"], "payments")
        return self._safe(item)

    def request_payment(self, invoice_id: str, amount: float,
                        approved: bool = False) -> dict[str, Any]:
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return {"allowed": False, "reason": "invoice_not_found"}
        if amount <= 0 or amount > invoice["amount"]:
            return {"allowed": False, "reason": "invalid_payment_amount"}
        decision = self.policy.evaluate("financial_transactions", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item = {"payment_id": f"PAY-{uuid.uuid4().hex[:10].upper()}",
                "invoice_id": invoice_id, "amount": amount,
                "status": "captured", "idempotency_key": uuid.uuid4().hex}
        self.payments[item["payment_id"]] = item
        self.lineage.record("payment.captured", "finance", "payment",
                            item["payment_id"], "payments", amount=amount)
        return self._safe(item)

    def request_refund(self, payment_id: str, amount: float,
                       approved: bool = False) -> dict[str, Any]:
        payment = self.payments.get(payment_id)
        if not payment:
            return {"allowed": False, "reason": "payment_not_found"}
        if amount <= 0 or amount > payment["amount"]:
            return {"allowed": False, "reason": "invalid_refund_amount"}
        decision = self.policy.evaluate("refund_transactions", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item = {"refund_id": f"REF-{uuid.uuid4().hex[:10].upper()}",
                "payment_id": payment_id, "amount": amount, "status": "processed"}
        self.refunds[item["refund_id"]] = item
        return self._safe(item)

    def post_ledger(self, debit: str, credit: str, amount: float) -> dict[str, Any]:
        if amount <= 0 or not debit or not credit or debit == credit:
            return {"allowed": False, "reason": "invalid_ledger_entry"}
        item = {"ledger_id": f"LED-{uuid.uuid4().hex[:10].upper()}",
                "debit": debit, "credit": credit, "amount": amount}
        self.ledger.append(item)
        self.lineage.record("ledger.posted", "finance", "ledger_entry",
                            item["ledger_id"], "payments", amount=amount)
        return self._safe(item)

    def reconcile(self, payment_id: str, ledger_id: str) -> dict[str, Any]:
        if payment_id not in self.payments:
            return {"allowed": False, "reason": "payment_not_found"}
        if not any(x["ledger_id"] == ledger_id for x in self.ledger):
            return {"allowed": False, "reason": "ledger_entry_not_found"}
        item = {"reconciliation_id": f"REC-{uuid.uuid4().hex[:10].upper()}",
                "payment_id": payment_id, "ledger_id": ledger_id, "status": "matched"}
        self.reconciliations.append(item)
        return self._safe(item)

    def set_budget(self, name: str, amount: float, approved: bool = False) -> dict[str, Any]:
        if amount < 0:
            return {"allowed": False, "reason": "invalid_budget"}
        decision = self.policy.evaluate("budget_change", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item = {"budget_id": f"BUD-{uuid.uuid4().hex[:10].upper()}",
                "name": name, "amount": amount, "status": "approved"}
        self.budgets[item["budget_id"]] = item
        return self._safe(item)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "accounts": len(self.accounts),
                "invoices": len(self.invoices), "payments": len(self.payments),
                "refunds": len(self.refunds), "ledger_entries": len(self.ledger),
                "reconciliations": len(self.reconciliations), "budgets": len(self.budgets),
                "credentials_exposed": False, "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): PaymentsFinancial._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [PaymentsFinancial._safe(v) for v in value]
        return value
