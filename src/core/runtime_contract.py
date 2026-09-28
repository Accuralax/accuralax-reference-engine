from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


_ALLOWED_STATUSES = {"received", "running", "awaiting_approval", "completed", "failed", "blocked"}
_ALLOWED_RISK = {"low", "medium", "high", "critical"}
_ALLOWED_APPROVAL = {"not_required", "pending", "approved", "rejected"}


@dataclass
class RuntimeExecutionContract:
    """Canonical envelope shared by gateway, supervisors, agents, tools and audit."""

    reference_id: str = field(default_factory=lambda: f"CFS-AI-{datetime.now(timezone.utc):%Y}-{uuid4().hex[:12].upper()}")
    request_id: str = field(default_factory=lambda: uuid4().hex)
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    tenant_id: str = "default"
    workspace_id: str = "default"
    actor_id: str = "system"
    channel: str = "internal"
    request: str = ""
    intent: str | None = None
    domain: str | None = None
    agent: str | None = None
    skill: str | None = None
    action: str | None = None
    status: str = "received"
    risk_level: str = "low"
    approval_state: str = "not_required"
    safety_status: str = "pending"
    verification_status: str | None = None
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    errors: list[str] = field(default_factory=list)
    credentials_exposed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.reference_id or not self.request_id or not self.trace_id:
            raise ValueError("reference_id, request_id and trace_id are required")
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError(f"Invalid runtime status: {self.status}")
        if self.risk_level not in _ALLOWED_RISK:
            raise ValueError(f"Invalid risk level: {self.risk_level}")
        if self.approval_state not in _ALLOWED_APPROVAL:
            raise ValueError(f"Invalid approval state: {self.approval_state}")
        if self.credentials_exposed:
            raise ValueError("credentials_exposed must remain False")
        if self.status == "awaiting_approval" and self.approval_state != "pending":
            raise ValueError("awaiting_approval requires pending approval state")

    def update(self, **changes: Any) -> "RuntimeExecutionContract":
        for key, value in changes.items():
            if not hasattr(self, key):
                raise ValueError(f"Unknown runtime contract field: {key}")
            setattr(self, key, value)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.validate()
        return self

    def add_policy_decision(self, decision: dict[str, Any]) -> None:
        self.policy_decisions.append(dict(decision))
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_tool_call(self, tool_call: dict[str, Any]) -> None:
        safe_call = dict(tool_call)
        safe_call.pop("credential", None)
        safe_call.pop("credentials", None)
        self.tool_calls.append(safe_call)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeExecutionContract":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def approve(self) -> None:
        self.approval_state = "approved"
        if self.status == "awaiting_approval":
            self.status = "running"
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.validate()

    def reject(self, reason: str = "approval_rejected") -> None:
        self.approval_state = "rejected"
        self.status = "blocked"
        self.errors.append(reason)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.validate()
