from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


@dataclass
class Offering:
    offering_id: str
    name: str
    kind: str
    status: str = "idea"
    pricing: dict[str, Any] = field(default_factory=dict)
    sla: dict[str, Any] = field(default_factory=dict)


class ProductService:
    """Governed product and service catalogue and lifecycle intelligence."""

    def __init__(self) -> None:
        self.offerings: dict[str, Offering] = {}
        self.releases: list[dict[str, Any]] = []
        self.subscriptions: list[dict[str, Any]] = []
        self.service_requests: list[dict[str, Any]] = []
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_offering(self, name: str, kind: str) -> dict[str, Any]:
        offering_id = f"OFF-{uuid.uuid4().hex[:10].upper()}"
        self.offerings[offering_id] = Offering(offering_id, name, kind)
        self.lineage.record("offering.created", "system", "product", offering_id, "product_service")
        return self._safe({"offering_id": offering_id, "name": name, "kind": kind, "status": "idea"})

    def activate(self, offering_id: str, approved: bool = False) -> dict[str, Any]:
        offering = self.offerings.get(offering_id)
        if not offering:
            return {"allowed": False, "reason": "offering_not_found"}
        action = "service_activation" if offering.kind == "service" else "product_activation"
        decision = self.policy.evaluate(action, approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        offering.status = "active"
        self.lineage.record("offering.activated", "operator", "product", offering_id, "product_service")
        return {"allowed": True, "offering_id": offering_id, "status": "active"}

    def set_pricing(self, offering_id: str, price: float, approved: bool = False) -> dict[str, Any]:
        offering = self.offerings.get(offering_id)
        if not offering:
            return {"allowed": False, "reason": "offering_not_found"}
        decision = self.policy.evaluate("pricing_change", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        offering.pricing = {"price": price, "currency": "ZAR"}
        self.lineage.record("pricing.changed", "operator", "product", offering_id,
                            "product_service", price=price)
        return {"allowed": True, "offering_id": offering_id, "pricing": offering.pricing}

    def set_sla(self, offering_id: str, target: str, approved: bool = False) -> dict[str, Any]:
        offering = self.offerings.get(offering_id)
        if not offering:
            return {"allowed": False, "reason": "offering_not_found"}
        if not approved:
            return {"allowed": False, "reason": "approval_required"}
        offering.sla = {"target": target}
        return {"allowed": True, "offering_id": offering_id, "sla": offering.sla}

    def create_release(self, offering_id: str, version: str) -> dict[str, Any]:
        if offering_id not in self.offerings:
            return {"allowed": False, "reason": "offering_not_found"}
        item = {"release_id": f"REL-{uuid.uuid4().hex[:10].upper()}",
                "offering_id": offering_id, "version": version, "status": "planned"}
        self.releases.append(item)
        return self._safe(item)

    def create_subscription(self, customer_id: str, offering_id: str) -> dict[str, Any]:
        if offering_id not in self.offerings:
            return {"allowed": False, "reason": "offering_not_found"}
        item = {"subscription_id": f"SUB-{uuid.uuid4().hex[:10].upper()}",
                "customer_id": customer_id, "offering_id": offering_id, "status": "trial"}
        self.subscriptions.append(item)
        return self._safe(item)

    def create_service_request(self, customer_id: str, offering_id: str, summary: str) -> dict[str, Any]:
        if offering_id not in self.offerings:
            return {"allowed": False, "reason": "offering_not_found"}
        item = {"request_id": f"REQ-{uuid.uuid4().hex[:10].upper()}",
                "customer_id": customer_id, "offering_id": offering_id,
                "summary": summary, "status": "open"}
        self.service_requests.append(item)
        return self._safe(item)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "offerings": len(self.offerings),
                "releases": len(self.releases), "subscriptions": len(self.subscriptions),
                "service_requests": len(self.service_requests),
                "credentials_exposed": False, "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ProductService._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ProductService._safe(v) for v in value]
        return value
