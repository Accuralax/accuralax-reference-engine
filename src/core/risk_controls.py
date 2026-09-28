from pathlib import Path
from typing import Any
import uuid
import yaml


class RiskControlManager:
    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "risk_controls.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.controls = {c["id"]: c for c in self.config.get("controls", [])}
        self.findings: list[dict[str, Any]] = []

    def assess(self, category: str, likelihood: str, impact: str) -> dict[str, Any]:
        ls = self.config["risk_management"]["scoring"]["likelihood"]
        ims = self.config["risk_management"]["scoring"]["impact"]
        if likelihood not in ls or impact not in ims:
            raise ValueError("invalid risk score")
        score = (ls.index(likelihood) + 1) * (ims.index(impact) + 1)
        level = "low" if score <= 4 else "medium" if score <= 9 else "high" if score <= 16 else "critical"
        return {"risk_id": f"RSK-{uuid.uuid4().hex[:10].upper()}", "category": category,
                "likelihood": likelihood, "impact": impact, "score": score, "level": level,
                "credentials_exposed": False}

    def controls_for(self, category: str) -> list[dict[str, Any]]:
        return [c for c in self.controls.values() if c.get("category") in {category, "governance"}]

    def create_finding(self, risk: dict[str, Any], control_id: str, evidence: str = "") -> dict[str, Any]:
        if control_id not in self.controls:
            raise ValueError("unknown control")
        finding = {"finding_id": f"FND-{uuid.uuid4().hex[:10].upper()}",
                   "risk_id": risk["risk_id"], "control_id": control_id,
                   "status": "open", "evidence": bool(evidence),
                   "remediation_required": True, "credentials_exposed": False}
        self.findings.append(finding)
        return finding

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "control_count": len(self.controls),
                "finding_count": len(self.findings), "evidence_required": True}
