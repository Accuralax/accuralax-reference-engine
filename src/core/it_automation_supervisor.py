from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .it_automation_rules import AutomationDecision, ITAutomationRules
from .it_event_bus import ITEvent


@dataclass
class AutomationRun:
    event_id: str
    status: str
    decisions: list[AutomationDecision] = field(default_factory=list)
    attempts: int = 0
    reason: str | None = None


class ITAutomationSupervisor:
    """Bounded supervisor for event-driven IT automation and escalation."""

    def __init__(
        self,
        rules: ITAutomationRules | None = None,
        *,
        max_attempts: int = 2,
        max_events_per_cycle: int = 8,
    ) -> None:
        self.rules = rules or ITAutomationRules()
        self.max_attempts = max_attempts
        self.max_events_per_cycle = max_events_per_cycle
        self.runs: dict[str, AutomationRun] = {}

    def handle(
        self,
        event: ITEvent,
        *,
        approved_rule_ids: set[str] | None = None,
    ) -> AutomationRun:
        previous = self.runs.get(event.event_id)
        if previous and previous.status in {"completed", "awaiting_approval", "failed", "escalated"}:
            return previous

        run = AutomationRun(event.event_id, "evaluating")
        self.runs[event.event_id] = run

        for attempt in range(1, self.max_attempts + 1):
            run.attempts = attempt
            try:
                decisions = self.rules.dispatch(
                    event,
                    approved_rule_ids=approved_rule_ids,
                )
                run.decisions = decisions
                if any(d.reason == "human_approval_required" for d in decisions):
                    run.status = "awaiting_approval"
                    run.reason = "human_approval_required"
                elif any(d.allowed for d in decisions):
                    run.status = "completed"
                else:
                    run.status = "completed"
                    run.reason = "no_action_required"
                return run
            except Exception as exc:
                run.reason = type(exc).__name__
                if attempt == self.max_attempts:
                    run.status = "escalated"
                    return run

        run.status = "failed"
        return run

    def should_escalate(self, run: AutomationRun) -> bool:
        return run.status == "escalated" or run.attempts >= self.max_attempts and run.status == "failed"

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "max_events_per_cycle": self.max_events_per_cycle,
            "bounded": True,
            "retry_policy": "bounded",
            "escalation_on_failure": True,
            "credentials_exposed": False,
            "external_effects": "gateway_only",
        }
