import unittest

from src.core.global_supervisor_graph import run_global_supervisor_graph


class GlobalSupervisorGraphTests(unittest.TestCase):
    def test_it_request_reaches_domain_supervisor_and_specialist(self):
        state = run_global_supervisor_graph("My laptop is not working")
        self.assertEqual(state["domain"], "it")
        self.assertTrue(state["specialist"])
        self.assertEqual(state["domain_supervisor_status"], "ready_for_specialist")
        self.assertEqual(state["status"], "ready_for_specialist")
        self.assertTrue(state["terminal"])
        self.assertIn("domain_supervisor", state["history"])
        self.assertIn("delegation", state["domain_supervisor_history"])

    def test_engineering_request_reaches_engineering_domain(self):
        state = run_global_supervisor_graph("I need a backend API")
        self.assertEqual(state["domain"], "engineering")
        self.assertEqual(state["domain_supervisor_status"], "ready_for_specialist")
        self.assertEqual(state["status"], "ready_for_specialist")

    def test_cybersecurity_request_reaches_cyber_domain(self):
        state = run_global_supervisor_graph("cybersecurity threat assessment")
        self.assertEqual(state["domain"], "cybersecurity")
        self.assertEqual(state["domain_supervisor_status"], "ready_for_specialist")
        self.assertEqual(state["status"], "ready_for_specialist")

    def test_ambiguous_request_stops(self):
        state = run_global_supervisor_graph("I need help")
        self.assertEqual(state["status"], "clarification_required")
        self.assertTrue(state["terminal"])

    def test_sensitive_action_waits_for_approval_at_domain(self):
        state = run_global_supervisor_graph(
            "I need a laptop device change",
            action="device_change",
            approved=False,
        )
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertEqual(state["domain_supervisor_status"], "awaiting_approval")
        self.assertEqual(state["verification_status"], "pending")
        self.assertFalse(state["terminal"])

    def test_approved_action_reaches_specialist(self):
        state = run_global_supervisor_graph(
            "I need a laptop device change",
            action="device_change",
            approved=True,
        )
        self.assertEqual(state["status"], "ready_for_specialist")
        self.assertEqual(state["domain_supervisor_status"], "ready_for_specialist")
        self.assertEqual(state["verification_status"], "pass")

    def test_global_delegation_limit_is_terminal(self):
        state = run_global_supervisor_graph("My laptop is not working", max_delegations=0)
        self.assertEqual(state["status"], "delegation_limit")
        self.assertEqual(state["reason"], "max_delegations_reached")
        self.assertTrue(state["terminal"])

    def test_credentials_are_never_exposed(self):
        state = run_global_supervisor_graph("My laptop is not working")
        self.assertFalse(state["credentials_exposed"])
        self.assertFalse(any("credential" in item.lower() for item in state["history"]))


if __name__ == "__main__":
    unittest.main()
