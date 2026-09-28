from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class RepairPlan:
    repair_id: str
    check_name: str
    classification: str
    risk: str
    action: str
    requires_approval: bool
    allowed: bool


class RepairPlanner:
    """Create bounded, non-executing repair plans from health findings."""

    SAFE_ACTIONS = {
        "configuration": "re-validate configuration and report the invalid file",
        "dependencies": "re-run dependency validation and prepare a dependency repair proposal",
        "files": "identify missing runtime files and prepare a restoration proposal",
        "execution_ledger": "rebuild ledger access metadata without deleting execution history",
        "agent_permissions": "stop and request human review of permission guardrails",
        "business_gateway": "stop and request human review of business capability guardrails",
        "python": "stop and request human review of runtime environment",
    }

    HIGH_RISK = {"agent_permissions", "business_gateway", "python"}

    def plan(self, report: dict[str, Any]) -> list[RepairPlan]:
        plans: list[RepairPlan] = []
        for check in report.get("checks", []):
            if check.get("status") != "fail":
                continue
            name = check["name"]
            risk = "high" if name in self.HIGH_RISK else "medium"
            plans.append(RepairPlan(
                repair_id=f"repair-{name}",
                check_name=name,
                classification="guardrail_sensitive" if risk == "high" else "bounded_runtime_repair",
                risk=risk,
                action=self.SAFE_ACTIONS.get(name, "request human diagnosis"),
                requires_approval=True,
                allowed=False if risk == "high" else True,
            ))
        return plans

    def snapshot(self, report: dict[str, Any]) -> dict[str, Any]:
        plans = self.plan(report)
        return {"repair_count": len(plans), "plans": [asdict(plan) for plan in plans], "execution_enabled": False}
