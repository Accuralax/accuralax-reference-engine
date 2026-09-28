from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


class SupabaseRuntimeAdapter:
    """Minimal REST adapter for the existing AccuraLax durable execution schema."""

    def __init__(self, url: str | None = None, service_key: str | None = None, timeout: int = 15):
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        self.timeout = max(3, min(int(timeout), 60))

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.key)

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "degraded", "configured": False, "reason": "supabase_credentials_not_configured"}
        try:
            self.select("omega_health_snapshots", {"select": "id", "limit": "1"})
            return {"status": "ok", "configured": True, "durable": True, "provider": "supabase"}
        except Exception as exc:
            return {"status": "failed", "configured": True, "durable": True, "reason": f"{type(exc).__name__}: {exc}"}

    def _request(self, method: str, table: str, *, query: str = "", body: Any = None,
                 prefer: str = "return=representation") -> Any:
        if not self.enabled:
            raise RuntimeError("supabase_not_configured")
        url = f"{self.url}/rest/v1/{table}"
        if query:
            url += "?" + query
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=data, method=method, headers={
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Prefer": prefer,
        })
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else []
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"supabase_http_{exc.code}: {detail[:1000]}") from exc
        except URLError as exc:
            raise RuntimeError(f"supabase_network_error: {exc}") from exc

    def select(self, table: str, params: dict[str, str]) -> Any:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._request("GET", table, query=query)

    def insert(self, table: str, row: dict[str, Any]) -> Any:
        return self._request("POST", table, body=row)

    def update(self, table: str, filters: dict[str, str], patch: dict[str, Any]) -> Any:
        query = "&".join(f"{k}={v}" for k, v in filters.items())
        return self._request("PATCH", table, query=query, body=patch)

    def enqueue(self, *, tenant_id: str, workspace_id: str, intent_code: str,
                payload: dict[str, Any], channel: str = "SYSTEM", actor_type: str = "SYSTEM",
                complexity_mode: str = "STANDARD", idempotency_key: str | None = None) -> dict[str, Any]:
        rid = "REQ-" + uuid.uuid4().hex[:16].upper()
        trace = "TRC-" + uuid.uuid4().hex[:16].upper()
        correlation = "COR-" + uuid.uuid4().hex[:16].upper()
        row = {
            "request_id": rid, "trace_id": trace, "correlation_id": correlation,
            "idempotency_key": idempotency_key or uuid.uuid4().hex,
            "tenant_id": tenant_id, "workspace_id": workspace_id,
            "channel": channel, "actor_type": actor_type, "actor_id": None,
            "intent_code": intent_code, "complexity_mode": complexity_mode,
            "payload": payload, "context": {}, "status": "RECEIVED",
            "response_contract": {},
        }
        result = self.insert("control_plane_requests", row)
        return {"status": "queued", "request_id": rid, "record": result}

    def claim_worker(self, worker_code: str, lease_seconds: int = 60) -> dict[str, Any]:
        until = (datetime.now(timezone.utc) + timedelta(seconds=max(5, min(int(lease_seconds), 900)))).isoformat()
        rows = self.select("omega_worker_leases", {
            "worker_code": f"eq.{worker_code}", "select": "*", "limit": "1"
        })
        if rows and rows[0].get("status") == "RUNNING" and rows[0].get("lease_until") and rows[0]["lease_until"] > datetime.now(timezone.utc).isoformat():
            return {"status": "blocked", "reason": "lease_held", "worker_code": worker_code}
        patch = {"status": "RUNNING", "lease_until": until, "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                 "last_error": None, "metadata": {"owner": "canonical-runtime"}}
        if rows:
            result = self.update("omega_worker_leases", {"worker_code": f"eq.{worker_code}"}, patch)
        else:
            patch["worker_code"] = worker_code
            result = self.insert("omega_worker_leases", patch)
        return {"status": "acquired", "worker_code": worker_code, "lease_until": until, "record": result}

    def heartbeat(self, worker_code: str, lease_seconds: int = 60) -> dict[str, Any]:
        until = (datetime.now(timezone.utc) + timedelta(seconds=max(5, min(int(lease_seconds), 900)))).isoformat()
        result = self.update("omega_worker_leases", {"worker_code": f"eq.{worker_code}", "status": "eq.RUNNING"},
                             {"lease_until": until, "heartbeat_at": datetime.now(timezone.utc).isoformat()})
        return {"status": "renewed" if result else "blocked", "lease_until": until}

    def release_worker(self, worker_code: str, *, error: str | None = None) -> dict[str, Any]:
        result = self.update("omega_worker_leases", {"worker_code": f"eq.{worker_code}"},
                             {"status": "IDLE", "lease_until": None, "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                              "last_error": error})
        return {"status": "released", "record": result}

    def audit(self, action: str, *, actor: str = "system", source_channel: str = "RUNTIME",
              success: bool = True, request_id: str | None = None, reference_id: str | None = None,
              details: dict[str, Any] | None = None) -> dict[str, Any]:
        row = {"reference_id": reference_id, "actor": actor, "action": action,
               "source_channel": source_channel, "success": bool(success),
               "request_id": request_id, "details": details or {}}
        return {"status": "recorded", "record": self.insert("audit_logs", row)}

    def snapshot(self, status: str, metrics: dict[str, Any], interventions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        row = {"status": status, "metrics": metrics, "interventions": interventions or []}
        return {"status": "recorded", "record": self.insert("omega_health_snapshots", row)}
