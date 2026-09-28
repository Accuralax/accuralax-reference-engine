import unittest

from src.core.business_skill_executor import BusinessSkillExecutor


class BusinessSkillExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = BusinessSkillExecutor()

    def test_valid_skill_attaches_rag_provenance(self) -> None:
        result = self.executor.execute_plan(
            function="strategy",
            specialist="strategy_agent",
            skill="planning",
            action="plan",
            request="Create a business strategy plan",
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.status, "planned")
        self.assertTrue(result.knowledge)
        self.assertFalse(result.credentials_exposed)

    def test_specialist_function_mismatch_denied(self) -> None:
        result = self.executor.execute_plan(
            function="finance",
            specialist="strategy_agent",
            skill="financial_analysis",
            action="analyze",
            request="Analyze finances",
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "specialist_function_mismatch")

    def test_skill_function_scope_denied(self) -> None:
        result = self.executor.execute_plan(
            function="strategy",
            specialist="strategy_agent",
            skill="financial_analysis",
            action="analyze",
            request="Analyze strategy",
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "function_scope_denied")

    def test_review_skill_waits_for_approval(self) -> None:
        result = self.executor.execute_plan(
            function="finance",
            specialist="finance_agent",
            skill="financial_analysis",
            action="financial_transaction",
            request="Prepare a financial transaction",
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.status, "awaiting_approval")
        self.assertTrue(result.human_review)

    def test_external_action_is_gateway_only(self) -> None:
        result = self.executor.execute_plan(
            function="sourcing",
            specialist="sourcing_agent",
            skill="procurement_analysis",
            action="procure",
            request="Source approved equipment",
        )
        self.assertTrue(result.allowed)
        self.assertTrue(result.gateway_required)
        self.assertFalse(result.credentials_exposed)

    def test_snapshot_is_credential_safe(self) -> None:
        snapshot = self.executor.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertTrue(snapshot["rag_provenance"])
