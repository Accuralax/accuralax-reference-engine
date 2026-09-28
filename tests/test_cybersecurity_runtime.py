import unittest

from src.core.cybersecurity_runtime import CybersecurityRuntime


class CybersecurityRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = CybersecurityRuntime()

    def test_security_knowledge_is_available_after_scope(self) -> None:
        state = self.runtime.start(authorized_scope=True)
        hits = self.runtime.retrieve_security_knowledge(state, "identity least privilege")
        self.assertTrue(hits)
        self.assertEqual(hits[0].domain, "identity")
        self.assertTrue(state.knowledge)

    def test_knowledge_is_blocked_without_scope(self) -> None:
        state = self.runtime.start(authorized_scope=False)
        self.assertEqual(self.runtime.retrieve_security_knowledge(state, "identity"), [])
        self.assertEqual(state.status, "scope_required")

    def test_validation_can_use_knowledge_before_product(self) -> None:
        state = self.runtime.start(authorized_scope=True)
        self.runtime.retrieve_security_knowledge(state, "endpoint hardening detection")
        self.runtime.run_validation(state, {"category": "endpoint", "summary": "control gap"})
        product = self.runtime.product_opportunity(state)
        self.assertIsNotNone(product)

    def test_snapshot_is_credential_safe(self) -> None:
        snapshot = self.runtime.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
