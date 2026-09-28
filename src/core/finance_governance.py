from typing import Any

from .enterprise_control_plane import EnterpriseControlPlane
from .governance_engine import GovernanceEngine
from .identity_access import IdentityAccessManager
from .risk_controls import RiskControlManager
from .event_lineage import EventLineage
from .finance_payments import FinancePayments


class GovernedFinance:
    """Finance facade enforcing identity, policy, risk and lineage before actions."""

    def __init__(self) -> None:
        self.finance = FinancePayments()
        self.control = EnterpriseControlPlane()
        self.policy = GovernanceEngine()
        self.iam = IdentityAccessManager()
        self.risk = RiskControlManager()
        self.lineage = EventLineage()

    def request_payment(self, actor_role: str, invoice_id: str, amount: str,
                        *, approved: bool = False) -> dict[str, Any]:
        identity = self.iam.authorize("human", actor_role, "approve")
        if not identity["allowed"]:
            return {"allowed": False, "stage": "identity", "identity": identity}
        policy = self.policy.evaluate("financial_transactions", approved=approved)
        if policy["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": policy}
        gate = self.control.authorize("payment.capture", external_side_effect=True,
                                      approved=approved)
        if not gate["allowed"]:
            return {"allowed": False, "stage": "control_plane", "control": gate}
        payment = self.finance.request_payment(invoice_id, amount, approved=True)
        self.lineage.record("payment.created", actor_role, "payment", payment["payment_id"],
                            "finance", amount=amount, invoice_id=invoice_id)
        return {"allowed": True, "payment": payment, "lineage": self.lineage.health()}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "finance": self.finance.health(),
                "control_plane": self.control.health(), "policy": self.policy.health(),
                "identity": self.iam.health(), "risk": self.risk.health(),
                "lineage": self.lineage.health()}
