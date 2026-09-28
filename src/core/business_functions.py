from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class BusinessFunctionDecision:
    function: str
    allowed: bool
    reason: str
    requires_approval: bool


class BusinessFunctionRegistry:
    """Bounded registry and authorization layer for the 15 core business functions."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "business_functions.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, function: str) -> dict[str, Any] | None:
        return self.data.get("functions", {}).get(function)

    def exists(self, function: str) -> bool:
        return self.get(function) is not None

    def select_by_capability(self, capability: str) -> str | None:
        for function, cfg in self.data.get("functions", {}).items():
            if capability in cfg.get("capabilities", []):
                return function
        return None

    def authorize(
        self,
        function: str,
        action: str,
        *,
        approved: bool = False,
    ) -> BusinessFunctionDecision:
        cfg = self.get(function)
        if not cfg:
            return BusinessFunctionDecision(function, False, "unknown_function", False)
        allowed_actions = set(cfg.get("actions", [])) | set(cfg.get("approval_actions", []))
        if action not in allowed_actions:
            return BusinessFunctionDecision(function, False, "action_not_allowed", False)
        if action in cfg.get("approval_actions", []) and not approved:
            return BusinessFunctionDecision(function, False, "human_approval_required", True)
        return BusinessFunctionDecision(function, True, "allowed", False)

    def snapshot(self) -> dict[str, Any]:
        policy = self.data.get("policy", {})
        return {
            "functions": sorted(self.data.get("functions", {})),
            "function_count": len(self.data.get("functions", {})),
            "default_action": policy.get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "provider_access": policy.get("provider_access", "gateway_only"),
            "production_access": policy.get("production_access", "gateway_only"),
            "human_approval_required_for": [
                "financial_transactions",
                "employment_decisions",
                "external_communications",
                "procurement_commitments",
                "production_release",
            ],
        }


def classify_business_function(request: str) -> str | None:
    """Select exactly one function; composite requests remain for supervisor decomposition."""
    text = request.lower()
    groups = {
        "strategy": ("strategy", "strategic plan", "business plan", "growth strategy", "market expansion"),
        "finance": ("finance", "budget", "accounting", "cash flow", "funding", "tax", "financial"),
        "sales_marketing": ("sales", "marketing", "seo", "social media", "campaign", "brand", "pricing", "lead generation"),
        "research_development": ("research", "r&d", "innovation", "prototype", "product discovery", "experiment"),
        "information_technology": ("information technology", "software", "system", "it", "cloud", "cybersecurity", "network"),
        "customer_service": ("customer service", "customer support", "complaint", "customer experience", "returns"),
        "human_resources": ("human resources", "hr", "recruitment", "employee", "performance management", "workforce"),
        "design": ("design", "ui", "ux", "creative", "graphic", "brand identity"),
        "communications": ("communications", "public relations", "pr", "media", "press release", "crisis communication"),
        "governance": ("governance", "policy", "accountability", "controls", "risk oversight", "decision rights"),
        "production": ("production", "manufacturing", "factory", "service delivery", "capacity planning"),
        "sourcing": ("sourcing", "procurement", "purchasing", "supplier", "supply chain"),
        "quality_management": ("quality management", "quality assurance", "quality control", "qa", "continuous improvement"),
        "distribution": ("distribution", "fulfillment", "delivery", "channels", "inventory"),
        "operations": ("operations", "process management", "workflow", "service operations", "day-to-day operations"),
    }
    import re
    matches = []
    for name, terms in groups.items():
        if any(re.search(r"\b" + re.escape(term) + r"\b", text) for term in terms):
            matches.append(name)
    return matches[0] if len(matches) == 1 else None
