import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from src.core.business_gateway import BusinessCapabilityGateway
from integrations.adapters.mock import build_mock_adapters
from integrations.router import IntegrationRouter


class IntegrationRouterTests(unittest.TestCase):
    def setUp(self):
        self.adapters = build_mock_adapters()
        self.router = IntegrationRouter(BusinessCapabilityGateway(), self.adapters)

    def test_read_is_routed_to_mock_adapter(self):
        result = self.router.execute("hubspot", "search_contact", {"email": "test@example.com"})
        self.assertTrue(result.authorized)
        self.assertTrue(result.result.data["mock"])
        self.assertEqual(len(self.adapters["hubspot"].calls), 1)

    def test_denied_action_never_reaches_adapter(self):
        result = self.router.execute("hubspot", "delete_everything", {})
        self.assertFalse(result.authorized)
        self.assertEqual(len(self.adapters["hubspot"].calls), 0)

    def test_side_effect_needs_approval_and_idempotency(self):
        result = self.router.execute("hubspot", "create_contact", {"email": "test@example.com"}, idempotency_key="idem-1")
        self.assertFalse(result.authorized)
        self.assertEqual(len(self.adapters["hubspot"].calls), 0)

    def test_approved_side_effect_reaches_adapter(self):
        result = self.router.execute("hubspot", "create_contact", {"email": "test@example.com"}, approved=True, idempotency_key="idem-1")
        self.assertTrue(result.authorized)
        self.assertTrue(result.result.data["mock"])
        self.assertEqual(len(self.adapters["hubspot"].calls), 1)


if __name__ == "__main__":
    unittest.main()
