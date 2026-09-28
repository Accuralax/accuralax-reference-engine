import unittest

from src.core.business_service_runtime import BusinessServiceRuntime


class BusinessServiceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = BusinessServiceRuntime()

    def test_strategy_request_is_triaged_with_knowledge(self):
        state = self.runtime.start("We need a strategic plan for growth")
        self.assertEqual(state.function, "strategy")
        self.assertEqual(state.specialist, "strategy_agent")
        self.assertEqual(state.status, "triaged")
        self.assertTrue(state.knowledge)
        self.assertTrue(state.active_skills)
        self.assertIn("planning", state.active_skills)
        self.assertTrue(state.verification_required)
        self.assertTrue(state.reference_id.startswith("CFS-BIZ-"))

    def test_ambiguous_request_requires_clarification(self):
        state = self.runtime.start("We need help")
        self.assertEqual(state.status, "clarification_required")

    def test_financial_action_requires_approval(self):
        state = self.runtime.start("We need finance and budgeting support")
        result = self.runtime.authorize_action(state, "financial_transaction")
        self.assertFalse(result["allowed"])
        self.assertTrue(result["requires_approval"])
        self.assertEqual(state.status, "awaiting_approval")

    def test_approved_financial_action_is_authorized(self):
        state = self.runtime.start("We need finance and budgeting support")
        result = self.runtime.authorize_action(state, "financial_transaction", approved=True)
        self.assertTrue(result["allowed"])
        self.assertEqual(state.status, "action_authorized")

    def test_snapshot_is_safe(self):
        snapshot = self.runtime.snapshot()
        self.assertEqual(snapshot["specialist_count"], 15)
        self.assertTrue(snapshot["provenance"])
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
