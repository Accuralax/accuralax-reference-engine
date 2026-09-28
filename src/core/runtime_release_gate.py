from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class GateResult:
    name: str
    passed: bool
    evidence: Any = None
    reason: str | None = None


class RuntimeReleaseGate:
    """Deterministic release gate for the unified runtime control plane."""

    def __init__(self):
        self.checks: list[tuple[str, Callable[[], Any]]] = []

    def register(self, name: str, check: Callable[[], Any]):
        self.checks.append((str(name), check))
        return self

    def evaluate(self):
        results = []
        for name, check in self.checks:
            try:
                evidence = check()
                passed = bool(evidence is True or evidence == "ok" or
                              (isinstance(evidence, dict) and evidence.get("status") in {"ok", "pass", "completed"}))
                results.append(GateResult(name, passed, evidence, None if passed else "check_failed"))
            except Exception as exc:
                results.append(GateResult(name, False, None, type(exc).__name__))
        return {
            "status": "pass" if results and all(r.passed for r in results) else "blocked",
            "checks": [r.__dict__ for r in results],
            "passed": sum(r.passed for r in results),
            "failed": sum(not r.passed for r in results),
            "release_allowed": bool(results) and all(r.passed for r in results),
        }

    def health(self):
        return {"status": "ok", "engine": "runtime-release-gate", "checks": len(self.checks)}
