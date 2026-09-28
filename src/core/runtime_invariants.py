from __future__ import annotations


class RuntimeInvariants:
    """Cross-layer invariants for the unified execution fabric."""

    def __init__(self):
        self.checks = []

    def register(self, name, check):
        self.checks.append((str(name), check))
        return self

    def evaluate(self):
        results = []
        for name, check in self.checks:
            try:
                evidence = check()
                passed = evidence is True or (
                    isinstance(evidence, dict)
                    and evidence.get("status") in {"ok", "healthy", "ready", "pass"}
                )
                results.append({"name": name, "passed": passed, "evidence": evidence})
            except Exception as exc:
                results.append({"name": name, "passed": False, "reason": type(exc).__name__})
        failed = [item for item in results if not item["passed"]]
        return {
            "status": "pass" if results and not failed else "blocked",
            "release_allowed": bool(results) and not failed,
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "checks": results,
        }

    def health(self):
        return {"status": "ok", "engine": "runtime-invariants", "registered": len(self.checks)}
