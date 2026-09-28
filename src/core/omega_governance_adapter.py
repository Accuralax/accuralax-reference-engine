from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen


class OmegaGovernanceAdapter:
    """Server-side bridge to the canonical Ω approval RPCs.

    No service key is ever accepted from request payloads. If Ω is not configured,
    callers can explicitly use the legacy compatibility gate instead.
    """

    def __init__(self, url: str | None = None, service_key: str | None = None):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.service_key)

    def _rpc(self, name: str, payload: dict) -> object:
        if not self.enabled:
            raise RuntimeError("omega_governance_not_configured")
        body = json.dumps(payload).encode("utf-8")
        req = Request(f"{self.url}/rest/v1/rpc/{name}", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("apikey", self.service_key)
        req.add_header("Authorization", f"Bearer {self.service_key}")
        with urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None

    def request_approval(self, job_id: str) -> object:
        return self._rpc("omega_request_approval", {"p_job_id": job_id})

    def decide_approval(self, approval_request_id: str, decision: str, approver_id: str) -> object:
        return self._rpc("omega_decide_approval", {
            "p_approval_request_id": approval_request_id,
            "p_decision": decision,
            "p_approver_id": approver_id,
        })
