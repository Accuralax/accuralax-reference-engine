from __future__ import annotations
from typing import Any
from core.business_gateway import BusinessCapabilityGateway
from .capability import resolve
from .adapters.base import BusinessSystemAdapter
from core.enterprise_integration_layer import EnterpriseIntegrationLayer

class IntegrationConvergence:
    """Canonical capability -> policy gate -> durable provider execution."""
    def __init__(self, gateway: BusinessCapabilityGateway | None = None,
                 adapters: dict[str, BusinessSystemAdapter] | None = None,
                 durable: EnterpriseIntegrationLayer | None = None):
        self.gateway = gateway or BusinessCapabilityGateway()
        self.adapters = adapters or {}
        self.durable = durable or EnterpriseIntegrationLayer()
        for system, adapter in self.adapters.items():
            self.durable.register_connector(
                system, lambda action, payload, job, a=adapter: _adapter_call(a, action, payload)
            )

    def dispatch(self, tenant: str, workspace: str, capability: str,
                 payload: dict[str, Any] | None = None, *, approved: bool = False,
                 idempotency_key: str | None = None) -> dict:
        binding = resolve(capability)
        if binding is None:
            return {"status":"denied","reason":"capability_unknown","capability":capability}
        decision = self.gateway.authorize(binding.system, binding.action,
                                          approved=approved, idempotency_key=idempotency_key)
        if not decision.allowed:
            return {"status":"denied","reason":decision.reason,
                    "capability":capability,"system":binding.system,"action":binding.action}
        if binding.system not in self.adapters:
            return {"status":"failed","reason":"adapter_not_configured","capability":capability}
        return self.durable.dispatch(tenant, workspace, binding.system, binding.action,
                                     payload or {}, idempotency_key=idempotency_key)

def _adapter_call(adapter, action, payload):
    result = adapter.execute(action, payload)
    if hasattr(result, "ok"):
        if not result.ok:
            raise RuntimeError(result.error or "adapter_execution_failed")
        return result.data
    return result
