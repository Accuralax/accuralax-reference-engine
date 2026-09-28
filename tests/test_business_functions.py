import unittest

from src.core.business_functions import BusinessFunctionRegistry, classify_business_function


class BusinessFunctionTests(unittest.TestCase):
    def setUp(self):
        self.registry = BusinessFunctionRegistry()

    def test_all_15_functions_exist(self):
        self.assertEqual(self.registry.snapshot()["function_count"], 15)

    def test_core_functions_are_present(self):
        for name in (
            "strategy", "finance", "sales_marketing", "research_development",
            "information_technology", "customer_service", "human_resources",
            "design", "communications", "governance", "production", "sourcing",
            "quality_management", "distribution", "operations",
        ):
            self.assertTrue(self.registry.exists(name), name)

    def test_capability_selection(self):
        self.assertEqual(self.registry.select_by_capability("strategy"), "strategy")
        self.assertEqual(self.registry.select_by_capability("procurement"), "sourcing")
        self.assertEqual(self.registry.select_by_capability("quality_control"), "quality_management")

    def test_financial_action_requires_approval(self):
        decision = self.registry.authorize("finance", "financial_transaction")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        approved = self.registry.authorize("finance", "financial_transaction", approved=True)
        self.assertTrue(approved.allowed)

    def test_unknown_action_is_denied(self):
        decision = self.registry.authorize("operations", "delete_everything")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "action_not_allowed")

    def test_classification(self):
        self.assertEqual(classify_business_function("We need a strategic plan"), "strategy")
        self.assertEqual(classify_business_function("Help us with procurement and suppliers"), "sourcing")
        self.assertEqual(classify_business_function("Build a quality assurance process"), "quality_management")
        self.assertEqual(classify_business_function("I need help"), None)

    def test_snapshot_is_credential_safe(self):
        snapshot = self.registry.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
