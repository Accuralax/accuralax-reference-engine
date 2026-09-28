from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.business_gateway import BusinessCapabilityGateway
from .adapters.base import AdapterResult, BusinessSystemAdapter


@dataclass(frozen=True)
class GatewayExecution:
    authorized: bool
    result: AdapterResult | None
    reason: str


class IntegrationRouter:
    """Authorizes business capabilities before dispatching to a provider adapter."""

    def __init__(self, gateway: BusinessCapabilityGateway, adapters: dict[str, BusinessSystemAdapter]) -> None:
        self.gateway = gateway
        self.adapters = adapters

    def execute(self, system: str, action: str, payload: dict[str, Any] | None = None, *, approved: bool = False, idempotency_key: str | None = None) -> GatewayExecution:
        decision = self.gateway.authorize(system, action, approved=approved, idempotency_key=idempotency_key)
        if not decision.allowed:
            return GatewayExecution(False, None, decision.reason)
        adapter = self.adapters.get(system)
        if not adapter:
            return GatewayExecution(False, None, "adapter_not_configured")
        result = adapter.execute(action, payload or {})
        return GatewayExecution(True, result, "executed")
