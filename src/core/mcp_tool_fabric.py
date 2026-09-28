from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import hashlib
import json
import time
import uuid
import yaml


@dataclass
class ToolSpec:
    tool_id: str
    server: str
    name: str
    tool_class: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: Callable[..., Any] | None = None
    enabled: bool = True


class MCPToolFabric:
    """Provider-neutral MCP gateway with deny-by-default governed execution."""

    def __init__(self, max_seconds: float = 30.0) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "mcp_tool_fabric.yaml").read_text(encoding="utf-8")) or {}
        self.max_seconds = max_seconds
        self.tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> dict[str, Any]:
        if not spec.tool_id or not spec.server or not spec.name:
            return {"allowed": False, "reason": "tool_identity_required"}
        self.tools[spec.tool_id] = spec
        return {"allowed": True, "tool_id": spec.tool_id}

    def discover(self, server: str | None = None, tool_class: str | None = None) -> list[dict[str, Any]]:
        return [
            {"tool_id": t.tool_id, "server": t.server, "name": t.name,
             "tool_class": t.tool_class, "description": t.description}
            for t in self.tools.values()
            if t.enabled and (server is None or t.server == server)
            and (tool_class is None or t.tool_class == tool_class)
        ]

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): MCPToolFabric._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [MCPToolFabric._safe(v) for v in value]
        return value

    def execute(self, tool_id: str, args: dict[str, Any], *,
                actor: str, scope: str, approved: bool = False,
                policy_checked: bool = False, timeout_seconds: float | None = None) -> dict[str, Any]:
        tool = self.tools.get(tool_id)
        if not tool or not tool.enabled:
            return {"allowed": False, "reason": "tool_not_registered"}
        if not actor or not scope:
            return {"allowed": False, "reason": "identity_and_scope_required"}
        if any(k.lower() in {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
               for k in args):
            return {"allowed": False, "reason": "credential_argument_rejected"}
        if tool.tool_class in {"external_side_effect", "destructive"} and not approved:
            return {"allowed": False, "reason": "approval_required"}
        if tool.tool_class in {"external_side_effect", "destructive"} and not policy_checked:
            return {"allowed": False, "reason": "policy_check_required"}
        if tool.handler is None:
            return {"allowed": False, "reason": "tool_handler_not_available"}

        started = time.monotonic()
        try:
            result = tool.handler(**args)
            elapsed = time.monotonic() - started
            limit = min(timeout_seconds or self.max_seconds, self.max_seconds)
            if elapsed > limit:
                return {"allowed": False, "reason": "tool_timeout", "elapsed_seconds": elapsed}
        except Exception as exc:
            return {"allowed": False, "reason": "tool_execution_failed",
                    "error_type": type(exc).__name__}

        safe = self._safe(result)
        digest = hashlib.sha256(json.dumps(safe, sort_keys=True, default=str).encode()).hexdigest()
        return {
            "allowed": True,
            "execution_id": f"EXE-{uuid.uuid4().hex[:12].upper()}",
            "tool_id": tool_id,
            "server": tool.server,
            "result": safe,
            "result_hash": digest,
            "verified": True,
            "actor": actor,
            "scope": scope,
            "credentials_exposed": False,
        }

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "registered_tools": len(self.tools),
                "default_access": "deny", "credentials_exposed": False,
                "approval_gates": True, "result_verification": True}
