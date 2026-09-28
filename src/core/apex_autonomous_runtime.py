from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from .agent_registry import AgentRegistry
from .apex_runtime_bootstrap import ApexRuntimeBootstrap
from .autonomous_developer import AutonomousDeveloper
from .canonical_worker import CanonicalOmegaWorker
from .continuous_runtime import ContinuousRuntime
from .model_gateway import ModelGateway
from .supabase_runtime_adapter import SupabaseRuntimeAdapter


class ApexAutonomousRuntime:
    """Unified APEX runtime for bounded continuous operation and self-development."""

    def __init__(self, project_root: str | Path | None = None):
        self.root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
        self.bootstrap = ApexRuntimeBootstrap()
        self.supabase = SupabaseRuntimeAdapter()
        self.models = ModelGateway()
        self.agents = AgentRegistry()
        self.developer = AutonomousDeveloper(self.root, model_gateway=self.models, agent_registry=self.agents,
                                             autonomous=self.bootstrap.autonomous_development)
        self.worker = CanonicalOmegaWorker()
        self.continuous = ContinuousRuntime(self.worker)
        self.running = False
        self.ticks = 0

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "execution_authority": "omega9",
            "apex": self.bootstrap.health(),
            "supabase": self.supabase.health(),
            "developer": self.developer.health(),
            "worker": self.worker.health(),
            "continuous": self.continuous.health(),
            "bounded": True,
            "fail_closed": True,
        }

    def readiness(self) -> dict[str, Any]:
        gates = self.bootstrap.gates()
        blocked = [name for name, gate in gates.items() if not gate.get("release_allowed", False)]
        supabase = self.supabase.health()
        return {
            "status": "ready" if not blocked else "blocked",
            "release_allowed": not blocked,
            "blocked_stages": blocked,
            "supabase": supabase,
            "execution_authority": "omega9",
            "self_development": self.developer.health(),
        }

    def submit(self, *, tenant_id: str, workspace_id: str, intent_code: str,
               payload: dict[str, Any], channel: str = "SYSTEM") -> dict[str, Any]:
        if self.supabase.enabled:
            return self.supabase.enqueue(tenant_id=tenant_id, workspace_id=workspace_id,
                                          intent_code=intent_code, payload=payload, channel=channel)
        return {"status": "degraded", "reason": "supabase_not_configured",
                "payload": payload, "intent_code": intent_code}

    def tick(self, *, tenant_id: str = "", workspace_id: str = "") -> dict[str, Any]:
        readiness = self.readiness()
        if readiness["status"] != "ready":
            return {"status": "blocked", "reason": "runtime_not_ready", "readiness": readiness}
        try:
            # CanonicalOmegaWorker owns lease acquisition and ? execution through
            # OmegaRuntimeAdapter. Do not claim/release a second lease here.
            result = self.continuous.tick(tenant_id, workspace_id)
            self.ticks += 1
            if self.supabase.enabled:
                self.supabase.snapshot("HEALTHY", {"tick": self.ticks, "worker": result.get("status")})
            return {"status": result.get("status", "completed"), "tick": self.ticks,
                    "lease": result.get("result", {}).get("lease"), "result": result}
        except Exception as exc:
            if self.supabase.enabled:
                self.supabase.snapshot("FAILED", {"tick": self.ticks},
                                       [{"type": "exception", "error": f"{type(exc).__name__}: {exc}"}])
            return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    def run(self, *, iterations: int = 1, interval_seconds: float = 1.0,
            tenant_id: str = "", workspace_id: str = "") -> dict[str, Any]:
        count = max(1, min(int(iterations), 10000))
        self.running = True
        results = []
        try:
            for index in range(count):
                result = self.tick(tenant_id=tenant_id, workspace_id=workspace_id)
                results.append(result)
                if index + 1 < count:
                    time.sleep(max(0.0, min(float(interval_seconds), 300.0)))
        finally:
            self.running = False
        return {"status": "completed", "iterations": len(results), "results": results}

    def run_forever(self, *, interval_seconds: float = 5.0,
                    tenant_id: str = "", workspace_id: str = "",
                    stop_condition: Callable[[], bool] | None = None) -> None:
        """Run continuously until an explicit stop condition or process termination."""
        self.running = True
        try:
            while self.running:
                if stop_condition and stop_condition():
                    break
                self.tick(tenant_id=tenant_id, workspace_id=workspace_id)
                time.sleep(max(0.5, min(float(interval_seconds), 300.0)))
        finally:
            self.running = False

    def stop(self) -> None:
        self.running = False
        self.continuous.stop()
