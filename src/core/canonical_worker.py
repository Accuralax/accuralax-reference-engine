from __future__ import annotations
from .omega_runtime_adapter import OmegaRuntimeAdapter


class CanonicalOmegaWorker:
    """Controlled local worker for the canonical Ω continuous execution plane."""
    def __init__(self, adapter: OmegaRuntimeAdapter | None = None, limit: int = 20, worker_code: str = "OMEGA_CORE_WORKER"):
        self.adapter = adapter or OmegaRuntimeAdapter()
        self.limit = max(1, min(int(limit), 100))
        self.worker_code = worker_code
        self.last_result = None

    def run_once(self, tenant_id: str = "", workspace_id: str = ""):
        if not self.adapter.enabled:
            return {"status": "degraded", "reason": "omega_runtime_not_configured"}
        lease = self.adapter.worker_tick(self.worker_code, self.limit)
        result = self.adapter.apex_tick()
        self.last_result = result
        return {"status": "completed", "engine": "canonical-omega-worker", "lease": lease, "result": result}

    def health(self):
        if not self.adapter.enabled:
            return {"status": "degraded", "engine": "canonical-omega-worker", "configured": False}
        try:
            health = self.adapter.health()
            return {"status": "ok", "engine": "canonical-omega-worker", "configured": True, "omega": health}
        except Exception as exc:
            return {"status": "failed", "engine": "canonical-omega-worker", "configured": True, "reason": str(exc)}

    def reconcile(self):
        if not self.adapter.enabled:
            return {"status": "degraded", "reason": "omega_runtime_not_configured"}
        return self.adapter.invariant_check()
