from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainDelegation:
    domain: str
    supervisor: str
    specialist: str | None
    allowed: bool
    reason: str
    requires_approval: bool


class DomainSupervisor:
    """Bounded supervisor registry for major CyberFusion operating domains."""

    CONFIG = {
        "cybersecurity": {
            "supervisor": "cybersecurity_supervisor_agent",
            "specialists": ["cybersecurity_triage_agent", "security_red_agent", "security_blue_agent", "security_purple_agent"],
            "max_delegations": 4,
        },
        "engineering": {
            "supervisor": "engineering_supervisor_agent",
            "specialists": [
                "frontend_developer_agent", "backend_developer_agent",
                "full_stack_developer_agent", "mobile_developer_agent",
                "devops_platform_agent", "data_ai_engineer_agent",
                "qa_engineer_agent", "cybersecurity_developer_agent",
                "embedded_iot_agent", "game_interactive_agent",
            ],
            "max_delegations": 5,
        },
        "data_platform": {
            "supervisor": "data_management_supervisor_agent",
            "specialists": [
                "data_management_agent", "cloud_architecture_agent",
                "blockchain_web3_agent", "domain_identity_agent",
                "network_engineering_agent", "storage_backup_agent",
                "data_security_privacy_agent", "platform_observability_agent",
            ],
            "max_delegations": 6,
        },
        "it": {
            "supervisor": "it_service_supervisor_agent",
            "specialists": ["it_support_agent", "it_technician_agent", "ict_agent", "mis_agent"],
            "max_delegations": 6,
        },
        "business": {
            "supervisor": "business_supervisor_agent",
            "specialists": [
                "strategy_agent", "finance_agent", "sales_marketing_agent",
                "research_development_agent", "information_technology_agent",
                "customer_service_agent", "human_resources_agent", "design_agent",
                "communications_agent", "governance_agent", "production_agent",
                "sourcing_agent", "quality_management_agent", "distribution_agent",
                "operations_agent",
            ],
            "max_delegations": 3,
        },
    }

    def __init__(self, domain: str) -> None:
        if domain not in self.CONFIG:
            raise ValueError("unknown_domain")
        self.domain = domain
        self.config = self.CONFIG[domain]

    def delegate(self, specialist: str | None, *, action: str | None = None, approved: bool = False, delegation_count: int = 0) -> DomainDelegation:
        if delegation_count >= self.config["max_delegations"]:
            return DomainDelegation(self.domain, self.config["supervisor"], specialist, False, "delegation_limit", False)
        if specialist not in self.config["specialists"]:
            return DomainDelegation(self.domain, self.config["supervisor"], specialist, False, "specialist_not_allowed", False)
        approval_actions = {
            "deploy", "publish", "production_change", "external_side_effect", "irreversible_action",
            "device_change", "configuration_change", "software_install", "integration_change",
            "infrastructure_change", "network_change", "firewall_change", "dns_change",
            "domain_purchase", "domain_transfer", "data_change", "workflow_change",
            "data_migration", "destructive_change", "transaction", "contract_deploy",
            "token_issuance", "wallet_change", "live_security_test",
        }
        if action in approval_actions and not approved:
            return DomainDelegation(self.domain, self.config["supervisor"], specialist, False, "human_approval_required", True)
        return DomainDelegation(self.domain, self.config["supervisor"], specialist, True, "delegated", False)

    def snapshot(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "supervisor": self.config["supervisor"],
            "specialists": list(self.config["specialists"]),
            "max_delegations": self.config["max_delegations"],
            "default_action": "deny",
            "credentials_exposed_to_agents": False,
            "production_access": "gateway_only",
        }


class DomainSupervisorRegistry:
    """Top-level registry; does not execute provider actions."""

    def __init__(self) -> None:
        self.supervisors = {domain: DomainSupervisor(domain) for domain in DomainSupervisor.CONFIG}

    def get(self, domain: str) -> DomainSupervisor | None:
        return self.supervisors.get(domain)

    def snapshot(self) -> dict[str, Any]:
        return {
            "domains": sorted(self.supervisors),
            "credentials_exposed_to_agents": False,
            "execution": "delegation_only",
        }
