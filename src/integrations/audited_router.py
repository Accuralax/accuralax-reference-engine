from __future__ import annotations

from typing import Any

from core.business_gateway import BusinessCapabilityGateway
from .adapters.base import AdapterResult, BusinessSystemAdapter
from .execution import AuditedExecutor


class AuditedIntegrationRouter:
    def __init__(self, gateway: BusinessCapabilityGateway, adapters: dict[str, BusinessSystemAdapter], executor: AuditedExecutor | None = None) -> None:
        self.gateway = gateway
        self.adapters = adapters
        self.executor = executor or AuditedExecutor()

    def execute(self, system: str, action: str, payload: dict[str, Any] | None = None, *, approved: bool = False, idempotency_key: str | None = None) -> dict[str, Any]:
        decision = self.gateway.authorize(system, action, approved=approved, idempotency_key=idempotency_key)
        if not decision.allowed:
            return {"authorized": False, "status": "denied", "reason": decision.reason}
        adapter = self.adapters.get(system)
        if not adapter:
            return {"authorized": False, "status": "failed", "reason": "adapter_not_configured"}
        result_holder: dict[str, AdapterResult] = {}
        def operation() -> None:
            result_holder["result"] = adapter.execute(action, payload or {})
            if not result_holder["result"].ok:
                raise RuntimeError(result_holder["result"].error or "adapter_execution_failed")
        receipt = self.executor.execute(system, action, idempotency_key or f"read-{system}-{action}-{hash(str(payload))}", operation)
        return {"authorized": True, "status": receipt.status, "receipt": receipt.public(), "result": {"ok": bool(result_holder.get("result") and result_holder.get("result").ok)}}
