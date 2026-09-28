from __future__ import annotations

from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class GovernanceRegulatory:
    """Governed policy, regulation, privacy and compliance intelligence."""

    def __init__(self) -> None:
        self.policies: dict[str, dict[str, Any]] = {}
        self.regulations: dict[str, dict[str, Any]] = {}
        self.obligations: list[dict[str, Any]] = []
        self.assessments: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.exceptions: list[dict[str, Any]] = []
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def register_policy(self, name: str, owner: str, source: str) -> dict[str, Any]:
        if not owner.strip() or not source.strip():
            return {"allowed": False, "reason": "owner_and_source_required"}
        item = {"policy_id": f"POL-{uuid.uuid4().hex[:10].upper()}",
                "name": name, "owner": owner, "source": source,
                "status": "draft"}
        self.policies[item["policy_id"]] = item
        return self._safe(item)

    def approve_policy(self, policy_id: str, approved: bool = False) -> dict[str, Any]:
        item = self.policies.get(policy_id)
        if not item:
            return {"allowed": False, "reason": "policy_not_found"}
        decision = self.policy.evaluate("policy_change", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item["status"] = "approved"
        return {"allowed": True, "policy_id": policy_id, "status": "approved"}

    def register_regulation(self, name: str, authority: str, effective_date: str) -> dict[str, Any]:
        if not authority.strip() or not effective_date.strip():
            return {"allowed": False, "reason": "authority_and_effective_date_required"}
        item = {"regulation_id": f"REG-{uuid.uuid4().hex[:10].upper()}",
                "name": name, "authority": authority,
                "effective_date": effective_date, "status": "identified"}
        self.regulations[item["regulation_id"]] = item
        return self._safe(item)

    def create_obligation(self, regulation_id: str, owner: str, description: str) -> dict[str, Any]:
        if regulation_id not in self.regulations:
            return {"allowed": False, "reason": "regulation_not_found"}
        item = {"obligation_id": f"OBL-{uuid.uuid4().hex[:10].upper()}",
                "regulation_id": regulation_id, "owner": owner,
                "description": description, "status": "assigned"}
        self.obligations.append(item)
        return self._safe(item)

    def assess_compliance(self, obligation_id: str, status: str, evidence: str) -> dict[str, Any]:
        if not evidence.strip():
            return {"allowed": False, "reason": "evidence_required"}
        if not any(x["obligation_id"] == obligation_id for x in self.obligations):
            return {"allowed": False, "reason": "obligation_not_found"}
        item = {"assessment_id": f"ASM-{uuid.uuid4().hex[:10].upper()}",
                "obligation_id": obligation_id, "status": status, "evidence": evidence}
        self.assessments.append(item)
        self.lineage.record("compliance.assessed", "compliance", "compliance_assessment",
                            item["assessment_id"], "governance")
        return self._safe(item)

    def record_evidence(self, assessment_id: str, source: str, reference: str) -> dict[str, Any]:
        if not any(x["assessment_id"] == assessment_id for x in self.assessments):
            return {"allowed": False, "reason": "assessment_not_found"}
        item = {"evidence_id": f"EVD-{uuid.uuid4().hex[:10].upper()}",
                "assessment_id": assessment_id, "source": source, "reference": reference}
        self.evidence.append(item)
        return self._safe(item)

    def request_exception(self, rule: str, reason: str, approved: bool = False) -> dict[str, Any]:
        decision = self.policy.evaluate("policy_exception", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item = {"exception_id": f"EXC-{uuid.uuid4().hex[:10].upper()}",
                "rule": rule, "reason": reason, "status": "approved"}
        self.exceptions.append(item)
        return self._safe(item)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "policies": len(self.policies),
                "regulations": len(self.regulations), "obligations": len(self.obligations),
                "assessments": len(self.assessments), "evidence": len(self.evidence),
                "exceptions": len(self.exceptions), "credentials_exposed": False,
                "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): GovernanceRegulatory._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [GovernanceRegulatory._safe(v) for v in value]
        return value
