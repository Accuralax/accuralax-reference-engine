from pathlib import Path
from typing import Any
from decimal import Decimal
import uuid
import yaml


class FinancePayments:
    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "finance_payments.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.invoices: dict[str, dict[str, Any]] = {}
        self.payments: dict[str, dict[str, Any]] = {}
        self.ledger: list[dict[str, Any]] = []

    def create_invoice(self, customer_id: str, amount: str, invoice_number: str) -> dict[str, Any]:
        if invoice_number in {v["invoice_number"] for v in self.invoices.values()}:
            raise ValueError("invoice_number must be unique")
        value = Decimal(amount)
        if value <= 0:
            raise ValueError("amount must be positive")
        item = {"invoice_id": f"INV-{uuid.uuid4().hex[:10].upper()}",
                "customer_id": customer_id, "invoice_number": invoice_number,
                "amount": str(value), "state": "issued", "currency": self.config["finance"]["default_currency"]}
        self.invoices[item["invoice_id"]] = item
        return item

    def request_payment(self, invoice_id: str, amount: str, *, approved: bool = False) -> dict[str, Any]:
        if invoice_id not in self.invoices:
            raise ValueError("unknown invoice")
        item = {"payment_id": f"PAY-{uuid.uuid4().hex[:10].upper()}", "invoice_id": invoice_id,
                "amount": str(Decimal(amount)), "state": "authorized" if approved else "pending",
                "approval_required": not approved, "credentials_exposed": False}
        self.payments[item["payment_id"]] = item
        return item

    def post_ledger(self, debit: str, credit: str, amount: str) -> dict[str, Any]:
        value = Decimal(amount)
        if value <= 0 or not debit or not credit or debit == credit:
            raise ValueError("invalid balanced ledger entry")
        entry = {"entry_id": f"LED-{uuid.uuid4().hex[:10].upper()}", "debit": debit,
                 "credit": credit, "amount": str(value), "currency": self.config["finance"]["default_currency"]}
        self.ledger.append(entry)
        return entry

    def reconcile(self, payment_id: str, ledger_entry_id: str | None) -> dict[str, Any]:
        state = "matched" if ledger_entry_id else "exception"
        return {"payment_id": payment_id, "ledger_entry_id": ledger_entry_id,
                "state": state, "review_required": state == "exception"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "invoice_count": len(self.invoices),
                "payment_count": len(self.payments), "ledger_entries": len(self.ledger),
                "immutable_ledger": True, "credentials_exposed": False}
