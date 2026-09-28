from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .it_event_bus import ITEvent


@dataclass(frozen=True)
class AutomationRule:
    rule_id: str
    event_type: str
    action: str
    requires_approval: bool = False
    max_runs_per_event: int = 1


@dataclass(frozen=True)
class AutomationDecision:
    rule_id: str
    allowed: bool
    action: str
    reason: str
    requires_approval: bool


class ITAutomationRules:
    """Bounded internal automation rules; external effects require a gateway and approval."""

    def __init__(self, max_rules_per_event: int = 8) -> None:
        self.rules: dict[str, AutomationRule] = {}
        self.handlers: dict[str, Callable[[ITEvent, AutomationRule], None]] = {}
        self.max_rules_per_event = max_rules_per_event
        self._runs: set[tuple[str, str]] = set()

    def add_rule(
        self,
        rule: AutomationRule,
        handler: Callable[[ITEvent, AutomationRule], None],
    ) -> None:
        existing = [r for r in self.rules.values() if r.event_type == rule.event_type]
        if len(existing) >= self.max_rules_per_event:
            raise ValueError("rule_limit_reached")
        if rule.rule_id in self.rules:
            raise ValueError("duplicate_rule_id")
        self.rules[rule.rule_id] = rule
        self.handlers[rule.rule_id] = handler

    def evaluate(self, event: ITEvent) -> list[AutomationDecision]:
        decisions: list[AutomationDecision] = []
        for rule in self.rules.values():
            if rule.event_type != event.event_type:
                continue
            key = (rule.rule_id, event.event_id)
            if key in self._runs:
                decisions.append(AutomationDecision(rule.rule_id, False, rule.action, "already_run", rule.requires_approval))
                continue
            if rule.requires_approval:
                decisions.append(AutomationDecision(rule.rule_id, False, rule.action, "human_approval_required", True))
                continue
            decisions.append(AutomationDecision(rule.rule_id, True, rule.action, "allowed", False))
        return decisions

    def dispatch(self, event: ITEvent, *, approved_rule_ids: set[str] | None = None) -> list[AutomationDecision]:
        approved = approved_rule_ids or set()
        decisions: list[AutomationDecision] = []
        for rule in self.rules.values():
            if rule.event_type != event.event_type:
                continue
            key = (rule.rule_id, event.event_id)
            if key in self._runs:
                decisions.append(AutomationDecision(rule.rule_id, False, rule.action, "already_run", rule.requires_approval))
                continue
            if rule.requires_approval and rule.rule_id not in approved:
                decisions.append(AutomationDecision(rule.rule_id, False, rule.action, "human_approval_required", True))
                continue
            handler = self.handlers[rule.rule_id]
            handler(event, rule)
            self._runs.add(key)
            decisions.append(AutomationDecision(rule.rule_id, True, rule.action, "executed", False))
        return decisions

    def snapshot(self) -> dict[str, Any]:
        return {
            "rule_count": len(self.rules),
            "max_rules_per_event": self.max_rules_per_event,
            "bounded": True,
            "idempotent_per_event": True,
            "credentials_exposed": False,
            "external_effects": "gateway_only",
        }
