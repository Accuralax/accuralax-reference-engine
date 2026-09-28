import unittest

from src.core.business_function_skills import BusinessSkillRegistry


class BusinessSkillTests(unittest.TestCase):
    def setUp(self):
        self.skills = BusinessSkillRegistry()

    def test_skill_registry_loads(self):
        self.assertGreaterEqual(self.skills.snapshot()["skill_count"], 15)

    def test_finance_gets_financial_analysis(self):
        self.assertIn("financial_analysis", self.skills.skills_for("finance"))

    def test_sourcing_gets_procurement_analysis(self):
        self.assertIn("procurement_analysis", self.skills.skills_for("sourcing"))

    def test_skill_scope_is_enforced(self):
        decision = self.skills.authorize("financial_analysis", "strategy", "analyze")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "function_scope_denied")

    def test_action_scope_is_enforced(self):
        decision = self.skills.authorize("planning", "strategy", "publish")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "action_scope_denied")

    def test_valid_skill_is_allowed(self):
        decision = self.skills.authorize("financial_analysis", "finance", "analyze")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.human_review)

    def test_action_filter(self):
        skills = self.skills.select("finance", "model")
        self.assertIn("financial_analysis", skills)

    def test_unknown_skill_denied(self):
        decision = self.skills.authorize("unknown_skill", "finance", "analyze")
        self.assertFalse(decision.allowed)

    def test_credentials_safe(self):
        self.assertFalse(self.skills.snapshot()["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
