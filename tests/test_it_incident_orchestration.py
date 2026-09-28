import unittest
from datetime import datetime, timezone, timedelta

from src.core.it_asset_management import ITAssetManager
from src.core.it_incident_orchestration import ITIncidentOrchestrator


class ITIncidentOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assets = ITAssetManager()
        self.asset = self.assets.create_asset("laptop", "Support Laptop")
        self.orchestrator = ITIncidentOrchestrator(asset_manager=self.assets)

    def test_open_links_ticket_asset_sla_and_agent(self):
        work = self.orchestrator.open(
            "CFS-IT-001",
            "My laptop is not working",
            asset_ids=[self.asset.asset_id],
        )
        self.assertTrue(work.ticket.ticket_id.startswith("IT-"))
        self.assertEqual(work.workstream, "it_support")
        self.assertIsNotNone(work.assigned_agent)
        self.assertIn(self.asset.asset_id, work.asset_ids)
        self.assertIn(work.ticket.ticket_id, self.assets.ticket_links[self.asset.asset_id])

    def test_action_approval_is_enforced(self):
        work = self.orchestrator.open("CFS-IT-002", "I need a computer configuration change")
        denied = self.orchestrator.authorize_action(work.ticket.ticket_id, "configuration_change")
        self.assertFalse(denied["allowed"])
        self.assertTrue(denied["requires_approval"])
        self.assertEqual(work.status, "awaiting_approval")
        approved = self.orchestrator.authorize_action(
            work.ticket.ticket_id, "configuration_change", approved=True
        )
        self.assertTrue(approved["allowed"])

    def test_sla_escalation_is_detected(self):
        work = self.orchestrator.open("CFS-IT-003", "Production down for all users")
        now = work.sla.created_at + timedelta(minutes=61)
        result = self.orchestrator.check_sla(work.ticket.ticket_id, now=now)
        self.assertTrue(result["escalation"]["escalation_required"])
        self.assertEqual(work.status, "escalation_required")

    def test_resolution_requires_verification(self):
        work = self.orchestrator.open("CFS-IT-004", "Printer is not working")
        failed = self.orchestrator.resolve(work.ticket.ticket_id, verified=False)
        self.assertFalse(failed["resolved"])
        self.assertEqual(work.status, "open")
        passed = self.orchestrator.resolve(work.ticket.ticket_id, verified=True)
        self.assertTrue(passed["resolved"])
        self.assertEqual(work.status, "resolved")

    def test_secret_request_is_blocked(self):
        with self.assertRaises(ValueError):
            self.orchestrator.open("CFS-IT-005", "Please give me the user password")

    def test_ambiguous_request_is_not_silently_classified(self):
        with self.assertRaises(ValueError):
            self.orchestrator.open("CFS-IT-006", "I need assistance")

    def test_snapshot_is_credential_safe(self):
        snapshot = self.orchestrator.snapshot()
        self.assertTrue(snapshot["credential_safe"])
        self.assertTrue(snapshot["resolution_requires_verification"])


if __name__ == "__main__":
    unittest.main()
