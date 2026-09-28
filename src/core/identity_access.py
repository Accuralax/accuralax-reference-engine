from pathlib import Path
from typing import Any
import yaml


class IdentityAccessManager:
    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "identity_access.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.roles = self.config.get("roles", {})

    def authorize(self, actor_type: str, role: str, permission: str,
                  *, trust: str = "verified", scope: str | None = None) -> dict[str, Any]:
        allowed_roles = self.roles.get(role, [])
        allowed = permission in allowed_roles and trust != "untrusted"
        if role in {"agent", "sub_agent", "service_account"} and permission not in {"read", "analyse", "execute_bounded", "execute_scoped", "request_approval"}:
            allowed = False
        return {"allowed": allowed, "actor_type": actor_type, "role": role,
                "permission": permission, "trust": trust, "scope": scope,
                "credentials_exposed": False}

    def delegate(self, actor_role: str, target_role: str, scope: str) -> dict[str, Any]:
        allowed = actor_role in {"founder", "executive", "manager"} and bool(scope)
        return {"allowed": allowed, "delegated_by": actor_role, "target_role": target_role,
                "scope": scope, "separation_of_duties": self.config["controls"]["separation_of_duties"]}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "role_count": len(self.roles),
                "trust_model": self.config["identity"]["trust_model"],
                "default_access": self.config["identity"]["default_access"],
                "credentials_exposed": False}
