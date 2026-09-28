import unittest

from src.core.it_automation_rules import AutomationRule, ITAutomationRules
from src.core.it_event_bus import ITEventBus


class ITAutomationRulesTests(unittest.TestCase):
    def test_rule_evaluates_and_dispatches_once(self):
        rules = ITAutomationRules()
        received = []
        rules.add_rule(AutomationRule("r1", "ticket_created", "create_internal_task"), lambda e, r: received.append(e.event_id))
        event = ITEventBus().publish("ticket_created", "CFS-IT-400", ticket_id="IT-400")
        decision = rules.dispatch(event)
        self.assertTrue(decision[0].allowed)
        self.assertEqual(len(received), 1)
        second = rules.dispatch(event)
        self.assertEqual(second[0].reason, "already_run")
        self.assertEqual(len(received), 1)

    def test_approval_rule_waits(self):
        rules = ITAutomationRules()
        rules.add_rule(AutomationRule("r2", "sla_breach", "notify_supervisor", requires_approval=True), lambda e, r: None)
        event = ITEventBus().publish("sla_breach", "CFS-IT-401", ticket_id="IT-401")
        decision = rules.dispatch(event)
        self.assertFalse(decision[0].allowed)
        self.assertEqual(decision[0].reason, "human_approval_required")
        approved = rules.dispatch(event, approved_rule_ids={"r2"})
        self.assertTrue(approved[0].allowed)

    def test_rule_limit(self):
        rules = ITAutomationRules(max_rules_per_event=1)
        rules.add_rule(AutomationRule("r1", "event", "a"), lambda e, r: None)
        with self.assertRaises(ValueError):
            rules.add_rule(AutomationRule("r2", "event", "b"), lambda e, r: None)

    def test_snapshot_is_safe(self):
        snapshot = ITAutomationRules().snapshot()
        self.assertTrue(snapshot["bounded"])
        self.assertTrue(snapshot["idempotent_per_event"])
        self.assertFalse(snapshot["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
