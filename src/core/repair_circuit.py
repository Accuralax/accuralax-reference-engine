from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RepairAuditEvent:
    repair_id: str
    event: str
    status: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


class RepairCircuitBreaker:
    """Bound repeated repair failures and retain an auditable lifecycle in memory."""

    def __init__(self, max_failures: int = 3):
        if max_failures < 1:
            raise ValueError("max_failures must be >= 1")
        self.max_failures = max_failures
        self.failures: dict[str, int] = {}
        self.events: list[RepairAuditEvent] = []

    def _record(self, repair_id: str, event: str, status: str, **details: Any) -> None:
        self.events.append(RepairAuditEvent(
            repair_id=repair_id,
            event=event,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
        ))

    def allow(self, repair_id: str) -> bool:
        allowed = self.failures.get(repair_id, 0) < self.max_failures
        self._record(repair_id, "attempt_check", "allowed" if allowed else "blocked",
                     failures=self.failures.get(repair_id, 0), max_failures=self.max_failures)
        return allowed

    def record_success(self, repair_id: str) -> None:
        self.failures.pop(repair_id, None)
        self._record(repair_id, "repair_verified", "success")

    def record_failure(self, repair_id: str, reason: str) -> None:
        count = self.failures.get(repair_id, 0) + 1
        self.failures[repair_id] = count
        self._record(repair_id, "repair_failed", "failure", reason=reason, failures=count)
        if count >= self.max_failures:
            self._record(repair_id, "circuit_opened", "escalate", failures=count)

    def audit_log(self, repair_id: str | None = None) -> list[RepairAuditEvent]:
        if repair_id is None:
            return list(self.events)
        return [event for event in self.events if event.repair_id == repair_id]

    def status(self, repair_id: str) -> str:
        return "open" if self.failures.get(repair_id, 0) >= self.max_failures else "closed"
