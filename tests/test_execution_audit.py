import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
import json

from src.core.business_gateway import BusinessCapabilityGateway
from integrations.adapters.mock import build_mock_adapters
from integrations.audited_router import AuditedIntegrationRouter
from integrations.execution import AuditedExecutor


class ExecutionAuditTests(unittest.TestCase):
    def setUp(self):
        self.adapters = build_mock_adapters()
        self.router = AuditedIntegrationRouter(BusinessCapabilityGateway(), self.adapters, AuditedExecutor())

    def test_execution_receipt_contains_trace(self):
        response = self.router.execute("hubspot", "search_contact", {"email": "test@example.com"})
        self.assertEqual(response["status"], "succeeded")
        self.assertTrue(response["receipt"]["execution_id"].startswith("exec_"))
        self.assertIn("system:hubspot", response["receipt"]["trace"])

    def test_same_idempotency_key_does_not_repeat_side_effect(self):
        payload = {"email": "test@example.com"}
        first = self.router.execute("hubspot", "create_contact", payload, approved=True, idempotency_key="idem-contact-1")
        second = self.router.execute("hubspot", "create_contact", payload, approved=True, idempotency_key="idem-contact-1")
        self.assertEqual(first["receipt"]["execution_id"], second["receipt"]["execution_id"])
        self.assertEqual(len(self.adapters["hubspot"].calls), 1)

    def test_denied_operation_has_no_adapter_call(self):
        response = self.router.execute("hubspot", "delete_everything", {}, idempotency_key="bad-1")
        self.assertEqual(response["status"], "denied")
        self.assertEqual(len(self.adapters["hubspot"].calls), 0)

    def test_secret_is_not_in_receipt(self):
        response = self.router.execute("hubspot", "search_contact", {"email": "test@example.com", "note": "token=SECRET"})
        self.assertNotIn("SECRET", json.dumps(response))


if __name__ == "__main__":
    unittest.main()
