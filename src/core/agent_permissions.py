from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AgentPolicy:
    agent_id: str
    role: str
    allowed_skills: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    can_delegate: bool
    max_delegations: int = 0
    requires_human_approval: bool = False


class AgentPermissionRegistry:
    """Capability registry: agents may only use explicitly granted skills/tools."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "agent_permissions.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, agent_id: str) -> AgentPolicy | None:
        item = self.data.get("agents", {}).get(agent_id)
        if not item:
            return None
        return AgentPolicy(
            agent_id=agent_id,
            role=item.get("role", "specialist"),
            allowed_skills=tuple(item.get("allowed_skills", ())),
            allowed_tools=tuple(item.get("allowed_tools", ())),
            can_delegate=bool(item.get("can_delegate", False)),
            max_delegations=int(item.get("max_delegations", 0)),
            requires_human_approval=bool(item.get("requires_human_approval", False)),
        )

    def can_use_skill(self, agent_id: str, skill_id: str) -> bool:
        policy = self.get(agent_id)
        return bool(policy and skill_id in policy.allowed_skills)

    def can_use_tool(self, agent_id: str, tool_id: str) -> bool:
        policy = self.get(agent_id)
        return bool(policy and tool_id in policy.allowed_tools)

    def can_delegate(self, agent_id: str, delegation_count: int = 0) -> bool:
        policy = self.get(agent_id)
        return bool(policy and policy.can_delegate and delegation_count < policy.max_delegations)

    def requires_approval(self, agent_id: str) -> bool:
        policy = self.get(agent_id)
        return bool(policy and policy.requires_human_approval)
