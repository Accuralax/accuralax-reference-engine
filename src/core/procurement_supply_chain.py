from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


@dataclass
class Supplier:
    supplier_id: str
    name: str
    status: str = "prospect"
    risk: str = "unassessed"
    metadata: dict[str, Any] = field(default_factory=dict)


class ProcurementSupplyChain:
    """Governed sourcing, purchasing, supplier and supply-chain intelligence."""

    def __init__(self) -> None:
        self.suppliers: dict[str, Supplier] = {}
        self.purchase_requests: list[dict[str, Any]] = []
        self.purchase_orders: list[dict[str, Any]] = []
        self.contracts: list[dict[str, Any]] = []
        self.shipments: list[dict[str, Any]] = []
        self.inventory: dict[str, dict[str, Any]] = {}
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_supplier(self, name: str) -> dict[str, Any]:
        supplier_id = f"SUP-{uuid.uuid4().hex[:10].upper()}"
        self.suppliers[supplier_id] = Supplier(supplier_id, name)
        self.lineage.record("supplier.created", "system", "supplier", supplier_id, "procurement")
        return self._safe({"supplier_id": supplier_id, "name": name, "status": "prospect"})

    def assess_supplier(self, supplier_id: str, risk: str, reviewed: bool = False) -> dict[str, Any]:
        supplier = self.suppliers.get(supplier_id)
        if not supplier:
            return {"allowed": False, "reason": "supplier_not_found"}
        if not reviewed:
            return {"allowed": False, "reason": "supplier_review_required"}
        supplier.risk = risk
        supplier.status = "active"
        self.lineage.record("supplier.assessed", "operator", "supplier", supplier_id,
                            "procurement", risk=risk)
        return {"allowed": True, "supplier_id": supplier_id, "risk": risk, "status": "active"}

    def create_purchase_request(self, requester: str, supplier_id: str,
                                amount: float, description: str) -> dict[str, Any]:
        if supplier_id not in self.suppliers:
            return {"allowed": False, "reason": "supplier_not_found"}
        item = {
            "request_id": f"PR-{uuid.uuid4().hex[:10].upper()}",
            "requester": requester, "supplier_id": supplier_id,
            "amount": amount, "description": description, "status": "draft",
        }
        self.purchase_requests.append(item)
        self.lineage.record("purchase_request.created", requester, "purchase_request",
                            item["request_id"], "procurement", amount=amount)
        return self._safe(item)

    def approve_purchase_request(self, request_id: str, approved: bool = False) -> dict[str, Any]:
        request = next((x for x in self.purchase_requests if x["request_id"] == request_id), None)
        if not request:
            return {"allowed": False, "reason": "request_not_found"}
        decision = self.policy.evaluate("purchase_approval", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        request["status"] = "approved"
        self.lineage.record("purchase_request.approved", "approver", "purchase_request",
                            request_id, "procurement")
        return {"allowed": True, "request_id": request_id, "status": "approved"}

    def create_purchase_order(self, request_id: str, approved: bool = False) -> dict[str, Any]:
        request = next((x for x in self.purchase_requests if x["request_id"] == request_id), None)
        if not request:
            return {"allowed": False, "reason": "request_not_found"}
        if request["status"] != "approved":
            return {"allowed": False, "reason": "purchase_request_not_approved"}
        decision = self.policy.evaluate("purchase_order", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        order = {
            "po_id": f"PO-{uuid.uuid4().hex[:10].upper()}",
            "request_id": request_id, "supplier_id": request["supplier_id"],
            "amount": request["amount"], "status": "approved",
        }
        self.purchase_orders.append(order)
        self.lineage.record("purchase_order.created", "approver", "purchase_order",
                            order["po_id"], "procurement", amount=request["amount"])
        return self._safe(order)

    def create_contract(self, supplier_id: str, title: str, approved: bool = False) -> dict[str, Any]:
        if supplier_id not in self.suppliers:
            return {"allowed": False, "reason": "supplier_not_found"}
        decision = self.policy.evaluate("contract_commitments", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        contract = {
            "contract_id": f"CON-{uuid.uuid4().hex[:10].upper()}",
            "supplier_id": supplier_id, "title": title, "status": "active",
        }
        self.contracts.append(contract)
        return self._safe(contract)

    def record_shipment(self, po_id: str, status: str = "planned") -> dict[str, Any]:
        shipment = {"shipment_id": f"SHP-{uuid.uuid4().hex[:10].upper()}",
                    "po_id": po_id, "status": status}
        self.shipments.append(shipment)
        return self._safe(shipment)

    def register_inventory(self, sku: str, quantity: int) -> dict[str, Any]:
        self.inventory[sku] = {"sku": sku, "quantity": quantity}
        return dict(self.inventory[sku])

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "suppliers": len(self.suppliers),
            "purchase_requests": len(self.purchase_requests),
            "purchase_orders": len(self.purchase_orders),
            "contracts": len(self.contracts),
            "shipments": len(self.shipments),
            "inventory_items": len(self.inventory),
            "credentials_exposed": False,
            "lineage": self.lineage.health(),
        }

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ProcurementSupplyChain._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ProcurementSupplyChain._safe(v) for v in value]
        return value
