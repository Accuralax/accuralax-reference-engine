"""HTTP API security boundary for local and production deployments."""
from __future__ import annotations
import hmac
import os
import base64
import json
import hashlib

from typing import Any
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthContext:
    subject: str
    tenant_id: str
    workspace_id: str
    method: str



class APISecurity:
    """Configurable API-key boundary; disabled by default for local development."""

    def __init__(self) -> None:
        self.mode = os.getenv("API_AUTH_MODE", "disabled").strip().lower()
        self.api_key = os.getenv("API_API_KEY", "")
        self.cors_origin = os.getenv("API_CORS_ORIGIN", "http://localhost:5173")
        self.bearer_token = os.getenv("API_BEARER_TOKEN", "")
        self.jwt_secret = os.getenv("API_JWT_SECRET", "")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if ((self.mode in {"", "disabled", "local"}) or (self.mode == "api_key" and bool(self.api_key)) or (self.mode == "bearer" and bool(self.bearer_token))) else "misconfigured",
            "auth_mode": self.mode,
            "api_key_configured": bool(self.api_key),
            "credentials_exposed": False,
            "bearer_configured": bool(self.bearer_token),
        }

    def authenticate(self, headers: dict[str, str]) -> tuple[AuthContext | None, str]:
        """Authenticate and derive an immutable request identity/scope context."""
        mode = self.mode
        if mode in {"", "disabled", "local"}:
            return AuthContext("local", headers.get("X-Tenant-ID", "default"), headers.get("X-Workspace-ID", "default"), "local"), "authenticated"
        if mode == "bearer":
            raw = headers.get("Authorization", "")
            token = raw[7:].strip() if raw.lower().startswith("bearer ") else None
            ok, reason = self.authorize_bearer(token)
            if not ok: return None, reason
            return AuthContext(headers.get("X-Principal-ID", "authenticated"), headers.get("X-Tenant-ID", "default"), headers.get("X-Workspace-ID", "default"), "bearer"), "authenticated"
        ok, reason = self.authorize(headers.get("X-API-Key"))
        if not ok: return None, reason
        return AuthContext(headers.get("X-Principal-ID", "api-key"), headers.get("X-Tenant-ID", "default"), headers.get("X-Workspace-ID", "default"), "api_key"), "authenticated"

    def authorize_bearer(self, supplied_token: str | None) -> tuple[bool, str]:
        if self.mode in {"", "disabled", "local"}:
            return True, "disabled"
        if self.mode != "bearer":
            return False, "unsupported_auth_mode"
        if not self.bearer_token:
            return False, "bearer_token_not_configured"
        if not supplied_token or not hmac.compare_digest(supplied_token, self.bearer_token):
            return False, "invalid_bearer_token"
        return True, "authenticated"

    def authorize(self, supplied_key: str | None) -> tuple[bool, str]:
        if self.mode in {"", "disabled", "local"}:
            return True, "disabled"
        if self.mode != "api_key":
            return False, "unsupported_auth_mode"
        if not self.api_key:
            return False, "api_key_not_configured"
        if not supplied_key or not hmac.compare_digest(supplied_key, self.api_key):
            return False, "invalid_api_key"
        return True, "authenticated"
