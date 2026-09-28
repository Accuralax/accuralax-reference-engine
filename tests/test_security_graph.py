import unittest

from src.core.security_graph import run_security_graph


class SecurityGraphTests(unittest.TestCase):
    def test_scope_is_required(self) -> None:
        state = run_security_graph("identity access review")
        self.assertEqual(state["status"], "scope_required")
        self.assertEqual(state["history"], ["scope", "audit"])

    def test_defensive_cycle_completes(self) -> None:
        state = run_security_graph("endpoint hardening detection", authorized_scope=True, domain="endpoint")
        self.assertEqual(state["status"], "product_opportunity_identified")
        self.assertIn("agent_authorization", state["history"])
        self.assertEqual(state["selected_agent"], "cybersecurity_triage_agent")
        self.assertTrue(state["authorization"]["allowed_skills"])
        self.assertIn("security_rag", state["history"])
        self.assertIn("purple_verify", state["history"])
        self.assertIn("remediation", state["history"])
        self.assertIsNotNone(state["product"])

    def test_live_red_testing_is_approval_gated(self) -> None:
        state = run_security_graph("web application validation", authorized_scope=True, domain="web", live_red_testing=True, approved=False)
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertNotIn("blue_defense", state["history"])

    def test_unknown_category_does_not_guess(self) -> None:
        state = run_security_graph("quantum pineapple telemetry", authorized_scope=True)
        self.assertEqual(state["status"], "blocked_classification")


if __name__ == "__main__":
    unittest.main()
