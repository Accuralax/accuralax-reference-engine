from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterResult:
    ok: bool
    system: str
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BusinessSystemAdapter(Protocol):
    system: str
    def execute(self, action: str, payload: dict[str, Any]) -> AdapterResult: ...


class MockBusinessAdapter:
    """Safe local adapter used for deterministic tests; never calls production APIs."""

    def __init__(self, system: str, actions: set[str]) -> None:
        self.system = system
        self.actions = actions
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, action: str, payload: dict[str, Any]) -> AdapterResult:
        if action not in self.actions:
            return AdapterResult(False, self.system, action, error="adapter_action_not_supported")
        self.calls.append((action, dict(payload)))
        return AdapterResult(True, self.system, action, data={"mock": True, "payload": dict(payload)})
