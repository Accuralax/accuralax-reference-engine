from __future__ import annotations

from typing import Any, Callable


class ApexRegressionGate:
    """Final deterministic gate combining health, convergence and regression checks."""

    def __init__(self, control_plane=None):
        self.control_plane = control_plane
        self.checks: list[tuple[str, Callable[[], Any]]] = []

    def register(self, name: str, check: Callable[[], Any]):
        self.checks.append((str(name), check))
        return self

    def evaluate(self):
        results = []
        if self.control_plane:
            health = self.control_plane.health()
            results.append({
                "name": "runtime_health",
                "passed": health["status"] == "healthy",
                "evidence": health,
            })
        for name, check in self.checks:
            try:
                evidence = check()
                passed = bool(evidence is True or
                              (isinstance(evidence, dict) and evidence.get("status") in {"ok", "pass", "completed", "healthy"}))
                results.append({"name": name, "passed": passed, "evidence": evidence})
            except Exception as exc:
                results.append({"name": name, "passed": False, "reason": type(exc).__name__})
        passed = sum(item["passed"] for item in results)
        failed = len(results) - passed
        return {
            "status": "pass" if results and failed == 0 else "blocked",
            "release_allowed": bool(results) and failed == 0,
            "passed": passed,
            "failed": failed,
            "checks": results,
        }
