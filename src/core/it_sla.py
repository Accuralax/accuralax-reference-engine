from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


SLA_TARGETS = {"critical": 60, "high": 240, "medium": 480, "low": 1440}


@dataclass
class SLACase:
    case_id: str
    priority: str
    created_at: datetime
    target_minutes: int
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class ITSLAManager:
    """Deterministic SLA clock and escalation policy; no external side effects."""

    def create_case(self, case_id: str, priority: str, *, created_at: datetime | None = None) -> SLACase:
        priority = priority if priority in SLA_TARGETS else "medium"
        created = created_at or datetime.now(timezone.utc)
        return SLACase(case_id, priority, created, SLA_TARGETS[priority])

    @staticmethod
    def deadline(case: SLACase) -> datetime:
        return case.created_at + timedelta(minutes=case.target_minutes)

    def acknowledge(self, case: SLACase, *, at: datetime | None = None) -> SLACase:
        case.acknowledged_at = at or datetime.now(timezone.utc)
        case.events.append({"event": "acknowledged", "at": case.acknowledged_at.isoformat()})
        return case

    def resolve(self, case: SLACase, *, at: datetime | None = None) -> SLACase:
        case.resolved_at = at or datetime.now(timezone.utc)
        case.events.append({"event": "resolved", "at": case.resolved_at.isoformat()})
        return case

    def status(self, case: SLACase, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now(timezone.utc)
        deadline = self.deadline(case)
        completed = case.resolved_at is not None
        breached = not completed and current > deadline
        remaining = int((deadline - current).total_seconds() // 60)
        if completed:
            state = "resolved"
        elif breached:
            state = "breached"
        elif remaining <= max(1, case.target_minutes // 4):
            state = "at_risk"
        else:
            state = "within_sla"
        return {
            "case_id": case.case_id,
            "priority": case.priority,
            "state": state,
            "deadline": deadline.isoformat(),
            "remaining_minutes": max(0, remaining),
            "breached": breached,
        }

    def escalate_if_needed(self, case: SLACase, *, now: datetime | None = None) -> dict[str, Any]:
        result = self.status(case, now=now)
        if result["state"] == "breached" and not case.escalated:
            case.escalated = True
            case.escalation_reason = "sla_breached"
            case.events.append({"event": "escalation_required", "reason": case.escalation_reason})
        return {
            "escalation_required": case.escalated,
            "reason": case.escalation_reason,
            "side_effect": False,
        }

    @staticmethod
    def snapshot() -> dict[str, Any]:
        return {
            "targets_minutes": dict(SLA_TARGETS),
            "clock": "deterministic",
            "external_notifications": "gateway_only",
            "automatic_external_side_effects": False,
            "audit_events": True,
        }
