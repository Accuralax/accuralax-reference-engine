import unittest

from src.core.business_supervisor_graph import run_business_supervisor_graph


class BusinessSupervisorGraphTests(unittest.TestCase):
    def test_strategy_reaches_strategy_agent(self):
        state = run_business_supervisor_graph("We need a strategic plan")
        self.assertEqual(state["function"], "strategy")
        self.assertEqual(state["specialist"], "strategy_agent")
        self.assertEqual(state["status"], "ready_for_specialist")
        self.assertEqual(state["verification_status"], "pass")

    def test_sourcing_reaches_sourcing_agent(self):
        state = run_business_supervisor_graph("Help us with procurement")
        self.assertEqual(state["function"], "sourcing")
        self.assertEqual(state["specialist"], "sourcing_agent")

    def test_financial_transaction_waits_for_approval(self):
        state = run_business_supervisor_graph(
            "We need finance support",
            action="financial_transaction",
            approved=False,
        )
        self.assertEqual(state["function"], "finance")
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertFalse(state["terminal"])

    def test_approved_financial_transaction_is_authorized(self):
        state = run_business_supervisor_graph(
            "We need finance support",
            action="financial_transaction",
            approved=True,
        )
        self.assertEqual(state["status"], "ready_for_specialist")
        self.assertEqual(state["verification_status"], "pass")

    def test_ambiguous_business_request_does_not_guess(self):
        state = run_business_supervisor_graph("We need help")
        self.assertEqual(state["status"], "clarification_required")
        self.assertTrue(state["terminal"])

    def test_delegation_limit(self):
        state = run_business_supervisor_graph("We need a strategic plan", max_delegations=0)
        self.assertEqual(state["status"], "delegation_limit")
        self.assertTrue(state["terminal"])

    def test_credentials_safe(self):
        state = run_business_supervisor_graph("We need a strategic plan")
        self.assertFalse(state["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
