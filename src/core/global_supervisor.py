from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .it_automation_supervisor import ITAutomationSupervisor, AutomationRun
from .engineering_team import EngineeringTeam
from .data_platform_team import DataPlatformTeam
from .it_support_team import ITSupportTeam, classify_it_request
from .cybersecurity_teams import CybersecurityTeamEngine
from .business_functions import BusinessFunctionRegistry, classify_business_function
from .business_function_team import BusinessFunctionTeam


@dataclass(frozen=True)
class GlobalRoute:
    domain: str
    specialist: str | None
    allowed: bool
    reason: str


class GlobalSupervisor:
    """Cross-domain orchestration boundary for CyberFusion specialist teams."""

    DOMAINS = {
        "it": "it_support",
        "cybersecurity": "cybersecurity",
        "engineering": "engineering",
        "data_platform": "data_platform",
        "business": "business",
    }

    def __init__(self) -> None:
        self.it_team = ITSupportTeam()
        self.engineering_team = EngineeringTeam()
        self.data_team = DataPlatformTeam()
        self.cyber_team = CybersecurityTeamEngine()
        self.business_functions = BusinessFunctionRegistry()
        self.business_team = BusinessFunctionTeam()
        self.automation = ITAutomationSupervisor()

    def classify(self, request: str) -> str | None:
        text = request.lower()
        groups = {
            "cybersecurity": ("cybersecurity", "security incident", "threat", "vulnerability", "phishing"),
            "engineering": ("frontend", "backend", "software", "app", "api", "developer", "code"),
            "data_platform": ("database", "cloud", "blockchain", "domain", "dns", "network", "backup", "data"),
            "it": ("helpdesk", "computer", "laptop", "printer", "ict", "mis", "it support"),
            "business": ("business", "consulting", "funding", "compliance", "tender", "customer"),
        }
        matches = [domain for domain, terms in groups.items() if any(term in text for term in terms)]
        return matches[0] if len(matches) == 1 else None

    def route(self, request: str) -> GlobalRoute:
        domain = self.classify(request)
        if not domain:
            return GlobalRoute("unknown", None, False, "clarification_required")
        if domain == "it":
            stream = classify_it_request(request) or "it_support"
            capability = {"it_support": "helpdesk", "it_technician": "endpoint_support", "ict": "ict", "mis": "mis"}[stream]
            specialist = self.it_team.select(capability)
        elif domain == "engineering":
            specialist = self.engineering_team.select("api")
        elif domain == "data_platform":
            specialist = self.data_team.select("cloud_architecture")
        elif domain == "cybersecurity":
            specialist = "cybersecurity_triage_agent"
        else:
            business_function = classify_business_function(request)
            specialist = self.business_team.select(business_function) if business_function else None
            if specialist is None and business_function:
                specialist = self.business_team.select("operations")
        if not specialist:
            return GlobalRoute(domain, None, False, "specialist_not_available")
        return GlobalRoute(domain, specialist, True, "routed")

    def authorize_domain_action(self, domain: str, specialist: str, action: str, *, approved: bool = False) -> dict[str, Any]:
        if domain == "it":
            decision = self.it_team.authorize(specialist, action, approved=approved)
        elif domain == "engineering":
            decision = self.engineering_team.authorize(specialist, action, approved=approved)
        elif domain == "data_platform":
            decision = self.data_team.authorize(specialist, action, approved=approved)
        elif domain == "cybersecurity":
            decision = self.cyber_team.authorize("red_team", action, approved=approved)
        else:
            return {"allowed": False, "reason": "business_action_requires_business_gateway"}
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "requires_approval": decision.requires_approval,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "domains": sorted(self.DOMAINS),
            "bounded": True,
            "default_action": "deny",
            "credentials_exposed_to_agents": False,
            "production_access": "gateway_only",
            "high_risk_actions": "human_approval",
            "audit_required": True,
        }
