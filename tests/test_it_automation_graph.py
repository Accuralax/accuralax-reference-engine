import unittest

from src.core.it_automation_graph import run_it_automation_graph
from src.core.it_automation_rules import AutomationRule, ITAutomationRules
from src.core.it_automation_supervisor import ITAutomationSupervisor
from src.core.it_event_bus import ITEventBus


class ITAutomationGraphTests(unittest.TestCase):
    def test_graph_executes_bounded_automation(self):
        rules = ITAutomationRules()
        rules.add_rule(AutomationRule("r1", "ticket_created", "internal_task"), lambda e, r: None)
        event = ITEventBus().publish("ticket_created", "CFS-IT-600", ticket_id="IT-600")
        state = run_it_automation_graph(event, supervisor=ITAutomationSupervisor(rules))
        self.assertEqual(state["status"], "completed")
        self.assertTrue(state["terminal"])
        self.assertEqual(state["attempts"], 1)
        self.assertIn("observe", state["history"])
        self.assertIn("execute", state["history"])
        self.assertIn("terminal", state["history"])

    def test_graph_surfaces_approval(self):
        rules = ITAutomationRules()
        rules.add_rule(
            AutomationRule("r2", "sla_breach", "notify_supervisor", requires_approval=True),
            lambda e, r: None,
        )
        event = ITEventBus().publish("sla_breach", "CFS-IT-601", ticket_id="IT-601")
        state = run_it_automation_graph(event, supervisor=ITAutomationSupervisor(rules))
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertTrue(state["approval_required"])
        self.assertTrue(state["terminal"])

    def test_missing_event_is_terminal_failure(self):
        from src.core.it_automation_graph import build_it_automation_graph
        state = build_it_automation_graph().invoke({"history": [], "cycle_count": 0})
        self.assertEqual(state["status"], "terminal_failure")
        self.assertTrue(state["terminal"])

    def test_cycle_limit_is_terminal(self):
        rules = ITAutomationRules()
        event = ITEventBus().publish("none", "CFS-IT-602")
        state = run_it_automation_graph(event, supervisor=ITAutomationSupervisor(rules), max_cycles=0)
        self.assertEqual(state["status"], "cycle_limit")
        self.assertEqual(state["reason"], "max_cycles_reached")
        self.assertTrue(state["terminal"])

    def test_graph_is_credential_safe(self):
        rules = ITAutomationRules()
        event = ITEventBus().publish("safe", "CFS-IT-603", payload={"token": "hidden"})
        state = run_it_automation_graph(event, supervisor=ITAutomationSupervisor(rules))
        self.assertFalse(state["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
