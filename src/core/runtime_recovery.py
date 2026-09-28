from __future__ import annotations

from datetime import datetime, timezone


class RuntimeRecovery:
    """Deterministic failure classification and bounded recovery coordinator."""

    def __init__(self, max_attempts=3):
        self.max_attempts = max(1, int(max_attempts))
        self.attempts = {}

    def classify(self, result):
        if not isinstance(result, dict):
            return {"class": "unknown", "recoverable": False}
        status = result.get("status")
        if status in {"completed", "ok", "healthy", "ready"}:
            return {"class": "success", "recoverable": False}
        if status in {"blocked", "awaiting_approval"}:
            return {"class": "governance", "recoverable": False}
        if status in {"failed", "degraded"}:
            return {"class": "transient", "recoverable": True}
        return {"class": "unknown", "recoverable": False}

    def recover(self, operation_id, operation, reconcile=None):
        count = self.attempts.get(operation_id, 0)
        if count >= self.max_attempts:
            return {"status": "blocked", "reason": "recovery_attempt_limit", "attempts": count}
        self.attempts[operation_id] = count + 1
        try:
            result = operation()
        except Exception as exc:
            result = {"status": "failed", "error": type(exc).__name__}
        classification = self.classify(result)
        if classification["recoverable"] and reconcile:
            reconciliation = reconcile()
        else:
            reconciliation = None
        return {
            "status": "recovered" if result.get("status") in {"completed", "ok", "healthy", "ready"} else result.get("status", "unknown"),
            "attempt": self.attempts[operation_id],
            "classification": classification,
            "result": result,
            "reconciliation": reconciliation,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def health(self):
        return {"status": "ok", "engine": "runtime-recovery", "max_attempts": self.max_attempts}
