from __future__ import annotations

from typing import Any, Callable

from .health import HealthEngine
from .runtime_release_gate import RuntimeReleaseGate


class RuntimeControlPlane:
    """Single readiness/control surface for the unified execution runtime."""

    def __init__(self, root=None):
        self.health_engine = HealthEngine(root)
        self.release_gate = RuntimeReleaseGate()

    def register_check(self, name: str, check: Callable[[], Any]):
        self.release_gate.register(name, check)
        return self

    def health(self):
        return self.health_engine.run()

    def readiness(self):
        health = self.health()
        release = self.release_gate.evaluate()
        return {
            "status": "ready" if health["status"] == "healthy" and release["release_allowed"] else "not_ready",
            "health": health,
            "release": release,
        }

    def release(self):
        result = self.release_gate.evaluate()
        if not result["release_allowed"]:
            return {"status": "blocked", **result}
        return {"status": "approved", **result}
