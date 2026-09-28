from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import yaml


@dataclass(frozen=True)
class ITDecision:
    agent_id: str
    allowed: bool
    reason: str
    requires_approval: bool


class ITSupportTeam:
    """Bounded registry and authorization boundary for IT, ICT and MIS specialists."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "it_support_agents.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self.data.get("agents", {}).get(agent_id)

    def select(self, capability: str) -> str | None:
        for agent_id, cfg in self.data.get("agents", {}).items():
            if capability in cfg.get("capabilities", []):
                return agent_id
        return None

    def authorize(self, agent_id: str, action: str, *, approved: bool = False) -> ITDecision:
        cfg = self.get(agent_id)
        if not cfg:
            return ITDecision(agent_id, False, "unknown_agent", False)
        if action not in cfg.get("allowed_actions", []):
            return ITDecision(agent_id, False, "action_not_allowed", False)
        if action in cfg.get("requires_approval_for", []):
            if not approved:
                return ITDecision(agent_id, False, "human_approval_required", True)
        return ITDecision(agent_id, True, "allowed", False)

    def snapshot(self) -> dict[str, Any]:
        policy = self.data.get("policy", {})
        return {
            "agents": sorted(self.data.get("agents", {})),
            "default_action": policy.get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "provider_access": policy.get("provider_access", "gateway_only"),
            "production_access": policy.get("production_access", "gateway_only"),
            "every_change": policy.get("every_change", "audit"),
            "every_resolution": policy.get("every_resolution", "verification"),
        }


def classify_it_request(request: str) -> str | None:
    """Return one IT workstream; composite requests should be decomposed by a runtime."""
    text = request.lower()
    groups = {
        "it_support": ("help", "support", "ticket", "login", "email", "software problem", "not working"),
        "it_technician": ("computer", "laptop", "printer", "hardware", "windows", "install", "device"),
        "ict": ("ict", "connectivity", "wifi", "internet", "network", "teams", "communications"),
        "mis": ("mis", "report", "dashboard", "management information", "data quality", "workflow", "records"),
    }
    matches = [name for name, terms in groups.items() if any(term in text for term in terms)]
    return matches[0] if len(matches) == 1 else None


def contains_secret_request(request: str) -> bool:
    """Detect common secret-collection requests without inspecting or storing secrets."""
    return bool(re.search(r"\b(password|api[ _-]?key|token|secret|cvv|card number)\b", request.lower()))
