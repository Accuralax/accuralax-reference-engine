import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import tempfile
import unittest

from src.core.business_gateway import BusinessCapabilityGateway
from integrations.adapters.mock import build_mock_adapters
from integrations.audited_router import AuditedIntegrationRouter
from integrations.execution import AuditedExecutor
from integrations.durable_ledger import SQLiteExecutionLedger


class DurableExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ledger = SQLiteExecutionLedger(Path(self.tmp.name) / "executions.sqlite3")
        self.adapters = build_mock_adapters()
        self.router = AuditedIntegrationRouter(BusinessCapabilityGateway(), self.adapters, AuditedExecutor(ledger))

    def tearDown(self):
        self.tmp.cleanup()

    def test_receipt_survives_new_ledger_and_executor(self):
        first = self.router.execute("hubspot", "create_contact", {"email": "durable@example.com"}, approved=True, idempotency_key="durable-1")
        new_ledger = SQLiteExecutionLedger(Path(self.tmp.name) / "executions.sqlite3")
        self.assertIsNotNone(new_ledger.get("durable-1"))
        self.assertEqual(new_ledger.get("durable-1").execution_id, first["receipt"]["execution_id"])

    def test_replay_after_reconstruction_does_not_execute_again(self):
        payload = {"email": "durable@example.com"}
        first = self.router.execute("hubspot", "create_contact", payload, approved=True, idempotency_key="durable-2")
        ledger2 = SQLiteExecutionLedger(Path(self.tmp.name) / "executions.sqlite3")
        router2 = AuditedIntegrationRouter(BusinessCapabilityGateway(), self.adapters, AuditedExecutor(ledger2))
        second = router2.execute("hubspot", "create_contact", payload, approved=True, idempotency_key="durable-2")
        self.assertEqual(first["receipt"]["execution_id"], second["receipt"]["execution_id"])
        self.assertEqual(len(self.adapters["hubspot"].calls), 1)

    def test_count(self):
        self.router.execute("hubspot", "search_contact", {"email": "a@example.com"})
        self.assertEqual(self.router.executor.ledger.count(), 1)


if __name__ == "__main__":
    unittest.main()
