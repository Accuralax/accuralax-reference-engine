from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class BusinessAgentDecision:
    agent_id: str
    allowed: bool
    reason: str
    requires_approval: bool


class BusinessFunctionTeam:
    """Bounded specialist registry for the 15 business functions."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "business_function_agents.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self.data.get("agents", {}).get(agent_id)

    def select(self, function: str) -> str | None:
        for agent_id, cfg in self.data.get("agents", {}).items():
            if cfg.get("function") == function:
                return agent_id
        return None

    def authorize(self, agent_id: str, action: str, *, approved: bool = False) -> BusinessAgentDecision:
        cfg = self.get(agent_id)
        if not cfg:
            return BusinessAgentDecision(agent_id, False, "unknown_agent", False)
        allowed = set(cfg.get("allowed_actions", [])) | set(cfg.get("approval_actions", []))
        if action not in allowed:
            return BusinessAgentDecision(agent_id, False, "action_not_allowed", False)
        if action in cfg.get("approval_actions", []) and not approved:
            return BusinessAgentDecision(agent_id, False, "human_approval_required", True)
        return BusinessAgentDecision(agent_id, True, "allowed", False)

    def snapshot(self) -> dict[str, Any]:
        policy = self.data.get("policy", {})
        return {
            "agents": sorted(self.data.get("agents", {})),
            "specialist_count": len(self.data.get("agents", {})) - 1,
            "supervisor": "business_operations_supervisor_agent",
            "default_action": policy.get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "production_access": policy.get("production_access", "gateway_only"),
            "every_change": policy.get("every_change", "audit"),
            "every_release": policy.get("every_release", "verification"),
        }
