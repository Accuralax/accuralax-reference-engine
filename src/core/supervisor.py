from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from .agent_permissions import AgentPermissionRegistry

@dataclass(frozen=True)
class DelegationDecision:
    allowed: bool
    reason: str
    parent_agent: str
    child_agent: str

class AgentSupervisor:
    """Bounded supervisor for specialist/sub-agent delegation."""

    def __init__(self, registry: AgentPermissionRegistry | None = None) -> None:
        self.registry = registry or AgentPermissionRegistry()

    def select_specialist(self, service_id: str | None) -> str:
        mapping = {
            "cybersecurity": "cybersecurity_triage_agent",
            "security_red": "security_red_agent",
            "security_blue": "security_blue_agent",
            "security_purple": "security_purple_agent",
            "ai_automation": "ai_automation_agent",
            "website": "digital_agent",
            "software_app": "digital_agent",
        }
        return mapping.get(service_id, "business_operations_agent")

    def select_security_agent(self, stage: str) -> str:
        return self.select_specialist(f"security_{stage}")

    def authorize_delegation(self, parent_agent: str, child_agent: str, count: int = 0) -> DelegationDecision:
        parent = self.registry.get(parent_agent)
        child = self.registry.get(child_agent)
        if not parent:
            return DelegationDecision(False, "unknown_parent_agent", parent_agent, child_agent)
        if not child:
            return DelegationDecision(False, "unknown_child_agent", parent_agent, child_agent)
        if not self.registry.can_delegate(parent_agent, count):
            return DelegationDecision(False, "delegation_not_permitted_or_budget_exceeded", parent_agent, child_agent)
        if child.role == "repair":
            return DelegationDecision(False, "repair_requires_human_approval", parent_agent, child_agent)
        return DelegationDecision(True, "delegation_allowed", parent_agent, child_agent)

    def security_authorization_snapshot(self, stage: str) -> dict[str, Any]:
        agent_id = self.select_security_agent(stage)
        snapshot = self.authorization_snapshot(agent_id)
        return {"stage": stage, **snapshot}

    def authorization_snapshot(self, agent_id: str) -> dict[str, Any]:
        policy = self.registry.get(agent_id)
        if not policy:
            return {"agent_id": agent_id, "status": "unknown"}
        return {
            "agent_id": agent_id,
            "role": policy.role,
            "allowed_skills": list(policy.allowed_skills),
            "allowed_tools": list(policy.allowed_tools),
            "can_delegate": policy.can_delegate,
            "max_delegations": policy.max_delegations,
            "requires_human_approval": policy.requires_human_approval,
        }
