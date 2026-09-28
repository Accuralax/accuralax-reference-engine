from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class PlatformDecision:
    agent_id: str
    allowed: bool
    reason: str
    requires_approval: bool


class DataPlatformTeam:
    """Bounded specialist registry for data, cloud, blockchain, domain and networking work."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "data_platform_agents.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self.data.get("agents", {}).get(agent_id)

    def select(self, capability: str) -> str | None:
        for agent_id, cfg in self.data.get("agents", {}).items():
            if capability in cfg.get("capabilities", []):
                return agent_id
        return None

    def authorize(self, agent_id: str, action: str, *, approved: bool = False) -> PlatformDecision:
        cfg = self.get(agent_id)
        if not cfg:
            return PlatformDecision(agent_id, False, "unknown_agent", False)
        if action not in cfg.get("allowed_actions", []):
            return PlatformDecision(agent_id, False, "action_not_allowed", False)
        if action in cfg.get("requires_approval_for", []):
            if not approved:
                return PlatformDecision(agent_id, False, "human_approval_required", True)
        return PlatformDecision(agent_id, True, "allowed", False)

    def snapshot(self) -> dict[str, Any]:
        policy = self.data.get("policy", {})
        return {
            "agents": sorted(self.data.get("agents", {})),
            "default_action": policy.get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "provider_access": policy.get("provider_access", "gateway_only"),
            "blockchain_value_transfer": policy.get("blockchain_value_transfer", "human_approval"),
            "domain_purchase": policy.get("domain_purchase", "human_approval"),
            "dns_changes": policy.get("dns_changes", "human_approval"),
            "network_changes": policy.get("network_changes", "human_approval"),
            "destructive_data_operations": policy.get("destructive_data_operations", "human_approval"),
        }


def generate_domain_candidates(name: str, tlds: tuple[str, ...] = ("com", "co.za", "ai", "app", "cloud")) -> list[str]:
    """Generate naming candidates only; availability and purchase require external verification and approval."""
    base = "".join(ch for ch in name.lower().strip() if ch.isalnum())
    if not base:
        return []
    candidates: list[str] = []
    for tld in tlds:
        candidates.append(f"{base}.{tld}")
    return candidates


def classify_platform_request(request: str) -> str | None:
    text = request.lower()
    groups = {
        "data_management": ("database", "data", "etl", "migration", "data quality", "catalog"),
        "cloud_architecture": ("cloud", "aws", "azure", "gcp", "infrastructure", "kubernetes"),
        "blockchain_web3": ("blockchain", "web3", "smart contract", "wallet", "token"),
        "domain_identity": ("domain", "dns", "subdomain", "ssl", "email dns"),
        "network_engineering": ("network", "vlan", "vpn", "firewall", "routing", "switch"),
        "storage_backup": ("backup", "restore", "storage", "disaster recovery", "replication"),
        "data_security_privacy": ("privacy", "encryption", "data protection", "retention", "access control"),
        "platform_observability": ("monitoring", "logs", "metrics", "tracing", "observability", "alert"),
    }
    matches = [group for group, terms in groups.items() if any(term in text for term in terms)]
    return matches[0] if len(matches) == 1 else None
