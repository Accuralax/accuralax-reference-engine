from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class EngineeringDecision:
    agent_id: str
    allowed: bool
    reason: str
    requires_approval: bool


class EngineeringTeam:
    """Bounded engineering-agent registry for internal and approved client work."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "engineering_agents.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self.data.get("agents", {}).get(agent_id)

    def exists(self, agent_id: str) -> bool:
        return self.get(agent_id) is not None

    def capabilities(self, agent_id: str) -> tuple[str, ...]:
        item = self.get(agent_id) or {}
        return tuple(item.get("capabilities", ()))

    def authorize(self, agent_id: str, action: str) -> EngineeringDecision:
        item = self.get(agent_id)
        if not item:
            return EngineeringDecision(agent_id, False, "unknown_agent", False)
        allowed = action in item.get("allowed_actions", ())
        approval = action in item.get("requires_approval_for", ())
        if not allowed:
            return EngineeringDecision(agent_id, False, "action_not_allowed", approval)
        return EngineeringDecision(agent_id, True, "allowed", approval)

    def select(self, capability: str) -> str | None:
        for agent_id, item in self.data.get("agents", {}).items():
            if capability in item.get("capabilities", ()):
                return agent_id
        return None

    def snapshot(self) -> dict[str, Any]:
        return {
            "agent_count": len(self.data.get("agents", {})),
            "agents": sorted(self.data.get("agents", {})),
            "default_action": self.data.get("policy", {}).get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "production_access": self.data.get("policy", {}).get("production_access", "gateway_only"),
            "destructive_actions": self.data.get("policy", {}).get("destructive_actions", "human_approval"),
            "release_gate": self.data.get("policy", {}).get("every_release", "qa_verification"),
        }
