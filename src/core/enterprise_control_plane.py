from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class EnterpriseControlPlane:
    """Central registry and policy boundary for enterprise capabilities."""

    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config_path = Path(config_path or root / "config" / "enterprise_capabilities.yaml")
        self.config = self._load()
        self.capabilities: dict[str, dict[str, Any]] = self.config.get("capabilities", {})
        self.rules = self.config.get("control_plane", {})

    def _load(self) -> dict[str, Any]:
        if yaml is None:
            raise RuntimeError("PyYAML is required for the enterprise capability registry")
        with self.config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def get(self, capability_id: str) -> dict[str, Any] | None:
        return self.capabilities.get(capability_id)

    def list_capabilities(self) -> list[str]:
        return sorted(self.capabilities)

    def authorize(self, action: str, *, high_risk: bool = False,
                  destructive: bool = False, external_side_effect: bool = False,
                  approved: bool = False) -> dict[str, Any]:
        reasons: list[str] = []
        if high_risk and not approved:
            reasons.append("high_risk_requires_approval")
        if destructive and not approved:
            reasons.append("destructive_requires_approval")
        if external_side_effect and self.rules.get("external_side_effects_require_policy_check", True) and not approved:
            reasons.append("external_side_effect_requires_approval")
        return {"action": action, "allowed": not reasons, "reasons": reasons,
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "capability_count": len(self.capabilities),
                "mandatory_controls": self.rules.get("mandatory", []),
                "credentials_exposed": False}
