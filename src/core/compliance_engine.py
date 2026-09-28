from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import yaml


class ComplianceEngine:
    """Governed compliance assessment, gap detection and risk/report generation."""

    STATUS = {"compliant", "partial", "non_compliant", "not_applicable", "unknown", "overdue"}

    def __init__(self, config_path=None):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "business_compliance_matrix.yaml")
        self.config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def assess(self, controls: list[dict[str, Any]]) -> dict[str, Any]:
        assessed = []
        for c in controls:
            item = dict(c)
            status = item.get("status", "unknown")
            if status not in self.STATUS:
                status = "unknown"
            item["status"] = status
            evidence = item.get("evidence")
            if not evidence:
                item["status"] = "unknown" if status == "compliant" else status
                item["evidence_gap"] = True
            else:
                item["evidence_gap"] = False
            item["risk"] = self._risk(item)
            assessed.append(item)

        gaps = [x for x in assessed if x["status"] in {"partial", "non_compliant", "unknown", "overdue"}]
        overdue = [x for x in assessed if x["status"] == "overdue"]
        evidence_gaps = [x for x in assessed if x["evidence_gap"]]
        risks = sorted([x for x in assessed if x["risk"]["level"] != "low"], key=lambda x: x["risk"]["score"], reverse=True)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "control_count": len(assessed),
            "compliance_matrix": assessed,
            "gap_report": gaps,
            "overdue": overdue,
            "evidence_gaps": evidence_gaps,
            "risk_report": risks,
            "executive_brief": self._brief(assessed),
            "remediation_plan": self._remediation(gaps),
            "audit_pack": self._audit_pack(assessed),
            "generated_content": True,
            "requires_human_review": True,
        }

    def _risk(self, control: dict[str, Any]) -> dict[str, Any]:
        status = control["status"]
        confidence = control.get("confidence", "low")
        impact = {"low": 1, "medium": 2, "high": 3}.get(str(control.get("impact", "medium")).lower(), 2)
        likelihood = {
            "compliant": 1, "not_applicable": 1, "partial": 2,
            "unknown": 2, "overdue": 3, "non_compliant": 3
        }[status]
        if confidence == "low" and status != "not_applicable":
            likelihood = min(3, likelihood + 1)
        score = impact * likelihood
        level = "low" if score <= 2 else "medium" if score <= 4 else "high"
        return {"score": score, "level": level, "impact": impact, "likelihood": likelihood}

    @staticmethod
    def _brief(items):
        total = len(items)
        compliant = sum(x["status"] == "compliant" for x in items)
        return {
            "controls": total,
            "compliant": compliant,
            "gaps": total - compliant,
            "high_risk": sum(x["risk"]["level"] == "high" for x in items),
            "statement": "AI-generated assessment requiring human review."
        }

    @staticmethod
    def _remediation(gaps):
        return [{
            "control_id": x.get("control_id"),
            "owner": x.get("owner"),
            "priority": x["risk"]["level"],
            "action": x.get("remediation") or "Collect evidence, assign an owner and define a corrective action.",
            "due_date": x.get("due_date"),
        } for x in gaps]

    @staticmethod
    def _audit_pack(items):
        return [{
            "control_id": x.get("control_id"),
            "status": x["status"],
            "evidence": x.get("evidence"),
            "source": x.get("source"),
            "confidence": x.get("confidence", "low"),
            "provenance_required": True,
        } for x in items]
