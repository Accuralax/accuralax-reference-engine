from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen


class OmegaRuntimeAdapter:
    """Privileged bridge from the local runtime to canonical Ω RPCs."""
    def __init__(self, url: str | None = None, service_key: str | None = None):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.service_key)

    def rpc(self, name: str, payload: dict | None = None):
        if not self.enabled:
            raise RuntimeError("omega_runtime_not_configured")
        req = Request(f"{self.url}/rest/v1/rpc/{name}", data=json.dumps(payload or {}).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("apikey", self.service_key)
        req.add_header("Authorization", f"Bearer {self.service_key}")
        with urlopen(req, timeout=20) as response:
            raw = response.read().decode()
        return json.loads(raw) if raw else None

    def worker_tick(self, worker_code: str = "OMEGA_CORE_WORKER", limit: int = 20):
        return self.rpc("omega_worker_tick", {"p_worker_code": worker_code, "p_limit": max(1, min(int(limit), 100))})

    def apex_tick(self):
        return self.rpc("omega_apex_unified_tick")

    def claim_work(self, limit: int = 20):
        return self.rpc("omega_apex_claim_work", {"p_limit": max(1, min(int(limit), 100))})

    def scheduler_tick(self):
        return self.rpc("omega_scheduler_tick")

    def health(self):
        return self.rpc("omega_health_check")

    def invariant_check(self):
        return self.rpc("omega_runtime_invariant_check")
