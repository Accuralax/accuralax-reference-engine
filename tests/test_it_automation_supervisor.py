import unittest

from src.core.it_automation_rules import AutomationRule, ITAutomationRules
from src.core.it_automation_supervisor import ITAutomationSupervisor
from src.core.it_event_bus import ITEventBus


class ITAutomationSupervisorTests(unittest.TestCase):
    def test_completed_run(self):
        rules = ITAutomationRules()
        called = []
        rules.add_rule(AutomationRule("r1", "ticket_created", "internal_task"), lambda e, r: called.append(1))
        event = ITEventBus().publish("ticket_created", "CFS-IT-500", ticket_id="IT-500")
        run = ITAutomationSupervisor(rules).handle(event)
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.attempts, 1)
        self.assertEqual(len(called), 1)

    def test_approval_is_escalated_to_review(self):
        rules = ITAutomationRules()
        rules.add_rule(AutomationRule("r2", "sla_breach", "notify_supervisor", requires_approval=True), lambda e, r: None)
        event = ITEventBus().publish("sla_breach", "CFS-IT-501", ticket_id="IT-501")
        run = ITAutomationSupervisor(rules).handle(event)
        self.assertEqual(run.status, "awaiting_approval")
        self.assertTrue("human_approval_required" in run.reason)

    def test_failed_handler_is_bounded_and_escalated(self):
        rules = ITAutomationRules()
        def fail(event, rule):
            raise RuntimeError("controlled_failure")
        rules.add_rule(AutomationRule("r3", "failure", "controlled_action"), fail)
        event = ITEventBus().publish("failure", "CFS-IT-502")
        run = ITAutomationSupervisor(rules, max_attempts=2).handle(event)
        self.assertEqual(run.status, "escalated")
        self.assertEqual(run.attempts, 2)
        self.assertTrue(run.reason)

    def test_same_event_is_not_reprocessed_after_terminal_state(self):
        rules = ITAutomationRules()
        count = []
        rules.add_rule(AutomationRule("r4", "event", "task"), lambda e, r: count.append(1))
        event = ITEventBus().publish("event", "CFS-IT-503")
        supervisor = ITAutomationSupervisor(rules)
        supervisor.handle(event)
        supervisor.handle(event)
        self.assertEqual(len(count), 1)

    def test_snapshot_is_safe(self):
        snapshot = ITAutomationSupervisor().snapshot()
        self.assertTrue(snapshot["bounded"])
        self.assertTrue(snapshot["escalation_on_failure"])
        self.assertFalse(snapshot["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
