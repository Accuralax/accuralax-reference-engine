from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CyberAction:
    team: str
    mode: str
    allowed: bool
    reason: str
    requires_approval: bool = False


@dataclass(frozen=True)
class SecurityProduct:
    product_id: str
    name: str
    purpose: str
    controls: tuple[str, ...]
    release_requires_approval: bool = True


class CybersecurityTeamEngine:
    """Bounded red/blue/purple security orchestration."""

    RED_ALLOWED = {
        "threat_modeling",
        "attack_path_simulation",
        "control_validation",
        "purple_team_exercise",
    }
    BLUE_ALLOWED = {
        "monitoring",
        "detection_engineering",
        "configuration_review",
        "incident_triage",
        "hardening",
        "recovery_validation",
    }
    PRODUCT_ALLOWED = {
        "control_design",
        "prototype",
        "test",
        "package",
        "documentation",
    }

    def authorize(
        self,
        team: str,
        mode: str,
        *,
        authorized_scope: bool,
        live_testing: bool = False,
    ) -> CyberAction:
        team = team.strip().lower()
        mode = mode.strip().lower()
        if not authorized_scope:
            return CyberAction(team, mode, False, "authorized_scope_required")
        if team == "red_team":
            if mode not in self.RED_ALLOWED:
                return CyberAction(team, mode, False, "red_team_mode_blocked")
            return CyberAction(team, mode, True, "authorized_simulation", live_testing)
        if team == "blue_team":
            if mode not in self.BLUE_ALLOWED:
                return CyberAction(team, mode, False, "blue_team_mode_blocked")
            return CyberAction(team, mode, True, "defensive_action_allowed")
        if team == "security_product_team":
            if mode not in self.PRODUCT_ALLOWED:
                return CyberAction(team, mode, False, "product_mode_blocked")
            needs_approval = mode in {"package", "prototype"}
            return CyberAction(team, mode, True, "defensive_product_work", needs_approval)
        if team == "purple_team":
            if mode != "purple_team_exercise":
                return CyberAction(team, mode, False, "purple_team_mode_blocked")
            return CyberAction(team, mode, True, "coordinated_validation", True)
        return CyberAction(team, mode, False, "unknown_security_team")

    def product_opportunity(self, finding: dict[str, Any]) -> SecurityProduct | None:
        """Turn a validated finding into a defensive product concept."""
        category = str(finding.get("category", "")).strip().lower()
        products = {
            "identity": SecurityProduct(
                "cfs-sec-identity",
                "CyberFusion Identity Guard",
                "Detect risky access patterns and recommend least-privilege controls.",
                ("access-review", "anomaly-detection", "least-privilege"),
            ),
            "endpoint": SecurityProduct(
                "cfs-sec-endpoint",
                "CyberFusion Endpoint Shield",
                "Validate endpoint hardening and defensive detection coverage.",
                ("baseline-checks", "detection-coverage", "recovery-validation"),
            ),
            "data": SecurityProduct(
                "cfs-sec-data",
                "CyberFusion Data Guard",
                "Map data controls, monitor policy compliance, and surface protection gaps.",
                ("data-classification", "policy-monitoring", "audit"),
            ),
            "web": SecurityProduct(
                "cfs-sec-web",
                "CyberFusion Web Shield",
                "Validate web security controls and report defensive gaps.",
                ("configuration-review", "detection", "security-baseline"),
            ),
        }
        return products.get(category)

    def snapshot(self) -> dict[str, Any]:
        return {
            "teams": ["red_team", "blue_team", "purple_team", "security_product_team"],
            "red_team": {"simulation_only": True, "max_iterations": 5},
            "blue_team": {"defensive_only": True, "max_iterations": 8},
            "product_release_requires_approval": True,
            "credentials_exposed_to_agents": False,
        }
