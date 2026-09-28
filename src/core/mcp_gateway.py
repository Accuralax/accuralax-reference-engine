from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class MCPDecision:
    allowed: bool
    reason: str
    requires_approval: bool
    side_effect: bool


class MCPGateway:
    """Policy boundary for MCP-connected systems; provider credentials stay outside agents."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "mcp_gateway.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def authorize(self, system: str, action: str, *, approved: bool = False, idempotency_key: str | None = None) -> MCPDecision:
        policy = self.data.get("policy", {})
        system_cfg = self.data.get("systems", {}).get(system)
        if not system_cfg:
            return MCPDecision(False, "unknown_system", False, False)
        declared_actions = set(system_cfg.get("actions", []))
        read_actions = set(system_cfg.get("read_actions", declared_actions))
        write_actions = set(system_cfg.get("write_actions", []))
        if action not in read_actions | write_actions:
            return MCPDecision(False, "action_not_allowed", False, False)
        side_effect = action not in self._read_actions(system_cfg)
        if action in declared_actions and action not in write_actions and any(action.lower().startswith(prefix) or f"_{prefix}" in action.lower() for prefix in ("create","update","delete","write","send","execute","post","put","patch","remove")):
            side_effect = True
        if side_effect:
            if not policy.get("require_idempotency_for_side_effects", True) or not idempotency_key:
                return MCPDecision(False, "idempotency_required", True, True)
            if policy.get("require_human_approval_for_side_effects", True) and not approved:
                return MCPDecision(False, "human_approval_required", True, True)
        return MCPDecision(True, "allowed", False, side_effect)

    @staticmethod
    def _read_actions(system_cfg: dict[str, Any]) -> set[str]:
        declared = set(system_cfg.get("actions", []))
        explicit_reads = system_cfg.get("read_actions")
        writes = set(system_cfg.get("write_actions", []))
        if explicit_reads is not None:
            return set(explicit_reads) - writes
        return declared - writes

    def snapshot(self) -> dict[str, Any]:
        return {
            "systems": sorted(self.data.get("systems", {})),
            "default_action": self.data.get("policy", {}).get("default_action", "deny"),
            "default_mode": self.data.get("policy", {}).get("default_mode", "read_only"),
            "credentials_exposed_to_agents": False,
            "audit_required": self.data.get("policy", {}).get("require_audit", True),
        }
