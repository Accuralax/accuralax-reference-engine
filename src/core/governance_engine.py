from pathlib import Path
from typing import Any
import yaml


class GovernanceEngine:
    """Evaluate governed actions against machine-readable policy rules."""

    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "governance_policies.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.rules = self.config.get("rules", {})

    def evaluate(self, action: str, *, context: dict[str, Any] | None = None,
                 approved: bool = False, human_reviewed: bool = False) -> dict[str, Any]:
        context = context or {}
        matches = []
        for key, rule in self.rules.items():
            if key.replace("_", " ") in action.lower() or key in action.lower():
                matches.append((key, rule))
        decisions = []
        reasons = []
        for key, rule in matches:
            decision = rule.get("decision", "deny")
            if decision == "deny":
                decisions.append("deny")
                reasons.append(key)
            elif decision == "require_approval" and not approved:
                decisions.append("require_approval")
                reasons.append(key)
            elif decision == "require_human_review" and not human_reviewed:
                decisions.append("require_human_review")
                reasons.append(key)
            elif decision == "policy_check":
                if not context.get("policy_check_passed", False):
                    decisions.append("policy_check")
                    reasons.append(key)
        if "deny" in decisions:
            outcome = "denied"
        elif "require_approval" in decisions:
            outcome = "awaiting_approval"
        elif "require_human_review" in decisions:
            outcome = "awaiting_human_review"
        elif "policy_check" in decisions:
            outcome = "policy_check_required"
        else:
            outcome = "allowed"
        return {"action": action, "outcome": outcome, "matched_policies": reasons,
                "human_reviewed": human_reviewed, "approved": approved,
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "rule_count": len(self.rules),
                "default_decision": self.config.get("governance", {}).get("default_decision", "deny"),
                "human_oversight": self.config.get("ethics", {}).get("human_oversight_required", True)}
