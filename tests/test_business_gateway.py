import unittest

from src.core.business_gateway import BusinessCapabilityGateway


class BusinessGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = BusinessCapabilityGateway()

    def test_read_capability_is_allowed(self):
        self.assertTrue(self.gateway.authorize("hubspot", "search_contact").allowed)

    def test_unknown_capability_is_denied(self):
        self.assertFalse(self.gateway.authorize("hubspot", "delete_everything").allowed)

    def test_side_effect_requires_idempotency(self):
        decision = self.gateway.authorize("hubspot", "create_contact", approved=True)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "idempotency_key_required")

    def test_side_effect_requires_approval(self):
        decision = self.gateway.authorize("hubspot", "create_contact", idempotency_key="idem-1")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "approval_required_for_side_effect")

    def test_approved_side_effect_is_allowed(self):
        decision = self.gateway.authorize("hubspot", "create_contact", approved=True, idempotency_key="idem-1")
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
