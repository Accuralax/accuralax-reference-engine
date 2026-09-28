from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import date, datetime, timezone
import hashlib
import json
import yaml


@dataclass
class ComplianceControl:
    control_id: str
    domain: str
    requirement: str
    owner: str
    status: str = "unknown"
    evidence: str = ""
    source: str = ""
    due_date: str = ""
    review_date: str = ""
    risk_id: str = ""
    remediation: str = ""
    confidence: str = "low"


class ComplianceRiskReportAgent:
    """Governed compliance matrix, risk register and report-generation engine."""

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "business_compliance_matrix.yaml").read_text(encoding="utf-8")) or {}
        self.controls: dict[str, ComplianceControl] = {}
        self.risks: dict[str, dict[str, Any]] = {}
        self.reports: list[dict[str, Any]] = []

    def add_control(self, control: ComplianceControl) -> dict[str, Any]:
        if not all([control.control_id, control.domain, control.requirement, control.owner]):
            return {"allowed": False, "reason": "control_identity_incomplete"}
        allowed = set(self.config["status"]["values"])
        if control.status not in allowed:
            return {"allowed": False, "reason": "invalid_status"}
        if not control.source and control.status in {"compliant", "partial", "non_compliant"}:
            return {"allowed": False, "reason": "source_required"}
        self.controls[control.control_id] = control
        return {"allowed": True, "control_id": control.control_id}

    def assess_risk(self, risk_id: str, likelihood: int, impact: int, description: str,
                    control_id: str = "") -> dict[str, Any]:
        if not 1 <= likelihood <= 5 or not 1 <= impact <= 5:
            return {"allowed": False, "reason": "risk_scale_must_be_1_to_5"}
        score = likelihood * impact
        level = "low" if score <= 4 else "medium" if score <= 9 else "high" if score <= 16 else "critical"
        self.risks[risk_id] = {
            "risk_id": risk_id, "description": description, "likelihood": likelihood,
            "impact": impact, "score": score, "level": level, "control_id": control_id,
            "status": "open",
        }
        return {"allowed": True, **self.risks[risk_id]}

    def matrix(self) -> list[dict[str, Any]]:
        return [self._safe(c.__dict__) for c in self.controls.values()]

    def gaps(self) -> list[dict[str, Any]]:
        today = date.today()
        result = []
        for c in self.controls.values():
            overdue = False
            if c.due_date:
                try:
                    overdue = date.fromisoformat(c.due_date) < today and c.status not in {"compliant", "not_applicable"}
                except ValueError:
                    overdue = False
            if c.status in {"partial", "non_compliant", "unknown", "overdue"} or overdue or not c.evidence:
                result.append({
                    "control_id": c.control_id, "domain": c.domain,
                    "status": "overdue" if overdue else c.status,
                    "evidence_gap": not bool(c.evidence), "remediation": c.remediation,
                })
        return result

    def generate_report(self, report_type: str = "executive_brief", *,
                        approved: bool = False) -> dict[str, Any]:
        gaps = self.gaps()
        risks = list(self.risks.values())
        report = {
            "report_id": f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "report_type": report_type,
            "generated_content": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "control_count": len(self.controls),
            "gap_count": len(gaps),
            "risk_count": len(risks),
            "critical_risks": sum(r["level"] == "critical" for r in risks),
            "high_risks": sum(r["level"] == "high" for r in risks),
            "matrix": self.matrix(),
            "gaps": gaps,
            "risks": self._safe(risks),
            "confidence": "medium" if self.controls else "low",
            "approved_for_external_publication": bool(approved),
            "credentials_exposed": False,
        }
        report["content_hash"] = hashlib.sha256(
            json.dumps(self._safe(report), sort_keys=True, default=str).encode()
        ).hexdigest()
        self.reports.append(report)
        return report

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "controls": len(self.controls), "risks": len(self.risks),
                "reports": len(self.reports), "evidence_required": True,
                "credentials_exposed": False}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ComplianceRiskReportAgent._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ComplianceRiskReportAgent._safe(v) for v in value]
        return value
