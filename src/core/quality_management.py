from __future__ import annotations

from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class QualityManagement:
    """Governed quality, audit, nonconformity and CAPA management."""

    def __init__(self) -> None:
        self.standards: dict[str, dict[str, Any]] = {}
        self.inspections: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.capas: list[dict[str, Any]] = []
        self.audits: list[dict[str, Any]] = []
        self.metrics: dict[str, dict[str, Any]] = {}
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_standard(self, name: str, version: str) -> dict[str, Any]:
        item = {"standard_id": f"STD-{uuid.uuid4().hex[:10].upper()}",
                "name": name, "version": version, "status": "active"}
        self.standards[item["standard_id"]] = item
        self.lineage.record("quality.standard.created", "system", "quality_standard",
                            item["standard_id"], "quality")
        return self._safe(item)

    def record_inspection(self, entity_id: str, result: str, evidence: str) -> dict[str, Any]:
        if not evidence.strip():
            return {"allowed": False, "reason": "evidence_required"}
        item = {"inspection_id": f"INS-{uuid.uuid4().hex[:10].upper()}",
                "entity_id": entity_id, "result": result, "evidence": evidence,
                "status": "completed"}
        self.inspections.append(item)
        self.lineage.record("quality.inspection.recorded", "inspector", "inspection",
                            item["inspection_id"], "quality")
        return self._safe(item)

    def create_finding(self, inspection_id: str, severity: str, description: str) -> dict[str, Any]:
        if not any(x["inspection_id"] == inspection_id for x in self.inspections):
            return {"allowed": False, "reason": "inspection_not_found"}
        item = {"finding_id": f"FND-{uuid.uuid4().hex[:10].upper()}",
                "inspection_id": inspection_id, "severity": severity,
                "description": description, "status": "open"}
        self.findings.append(item)
        self.lineage.record("quality.finding.created", "inspector", "finding",
                            item["finding_id"], "quality")
        return self._safe(item)

    def create_capa(self, finding_id: str, owner: str, action: str,
                    approved: bool = False) -> dict[str, Any]:
        if not any(x["finding_id"] == finding_id for x in self.findings):
            return {"allowed": False, "reason": "finding_not_found"}
        if not owner.strip():
            return {"allowed": False, "reason": "owner_required"}
        if not approved:
            return {"allowed": False, "reason": "approval_required"}
        item = {"capa_id": f"CAPA-{uuid.uuid4().hex[:10].upper()}",
                "finding_id": finding_id, "owner": owner, "action": action,
                "status": "approved"}
        self.capas.append(item)
        return self._safe(item)

    def verify_capa(self, capa_id: str, effective: bool,
                    approved: bool = False) -> dict[str, Any]:
        capa = next((x for x in self.capas if x["capa_id"] == capa_id), None)
        if not capa:
            return {"allowed": False, "reason": "capa_not_found"}
        if not approved:
            return {"allowed": False, "reason": "approval_required"}
        capa["status"] = "closed" if effective else "effectiveness_review"
        return {"allowed": True, "capa_id": capa_id, "status": capa["status"]}

    def create_audit(self, scope: str) -> dict[str, Any]:
        item = {"audit_id": f"AUD-{uuid.uuid4().hex[:10].upper()}",
                "scope": scope, "status": "planned"}
        self.audits.append(item)
        return self._safe(item)

    def register_metric(self, metric_id: str, value: float, definition: str) -> dict[str, Any]:
        if not definition.strip():
            return {"allowed": False, "reason": "definition_required"}
        item = {"metric_id": metric_id, "value": value, "definition": definition}
        self.metrics[metric_id] = item
        return self._safe(item)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "standards": len(self.standards),
                "inspections": len(self.inspections), "findings": len(self.findings),
                "capas": len(self.capas), "audits": len(self.audits),
                "metrics": len(self.metrics), "credentials_exposed": False,
                "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): QualityManagement._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [QualityManagement._safe(v) for v in value]
        return value
