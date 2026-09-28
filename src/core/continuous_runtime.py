from __future__ import annotations

import time
from typing import Any, Callable


class ContinuousRuntime:
    """Bounded continuous execution loop around the canonical worker."""

    def __init__(self, worker, control_plane=None, interval_seconds: float = 1.0):
        self.worker = worker
        self.control_plane = control_plane
        self.interval_seconds = max(0.0, float(interval_seconds))
        self.running = False
        self.ticks = 0
        self.last_result = None

    def tick(self, tenant_id: str = "", workspace_id: str = ""):
        if self.control_plane:
            readiness = self.control_plane.readiness()
            if readiness["status"] != "ready":
                return {"status": "blocked", "reason": "runtime_not_ready", "readiness": readiness}
        result = self.worker.run_once(tenant_id, workspace_id)
        self.ticks += 1
        self.last_result = result
        return {"status": result.get("status", "completed"), "tick": self.ticks, "result": result}

    def run(self, iterations: int = 1, tenant_id: str = "", workspace_id: str = "", sleep: bool = False):
        count = max(1, min(int(iterations), 1000))
        self.running = True
        results = []
        try:
            for index in range(count):
                result = self.tick(tenant_id, workspace_id)
                results.append(result)
                if sleep and index + 1 < count:
                    time.sleep(self.interval_seconds)
        finally:
            self.running = False
        return {"status": "completed", "iterations": len(results), "results": results}

    def stop(self):
        self.running = False

    def reconcile(self):
        """Reconcile the canonical worker state without executing new work."""
        reconcile = getattr(self.worker, "reconcile", None)
        if callable(reconcile):
            return reconcile()
        return {"status": "ok", "reconciled": False, "reason": "worker_has_no_reconcile"}

    def health(self):
        return {"status": "ok", "engine": "continuous-runtime", "running": self.running, "ticks": self.ticks}
