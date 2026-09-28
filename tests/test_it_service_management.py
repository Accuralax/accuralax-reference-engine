import unittest

from src.core.it_service_management import ITServiceManager


class ITServiceManagementTests(unittest.TestCase):
    def setUp(self):
        self.manager = ITServiceManager()

    def test_incident_ticket(self):
        ticket = self.manager.create_ticket("CFS-IT-1", "email service is not working")
        self.assertEqual(ticket.ticket_type, "incident")
        self.assertEqual(ticket.priority, "medium")
        self.assertEqual(ticket.status, "open")

    def test_service_request(self):
        self.assertEqual(self.manager.classify_ticket_type("install a printer"), "service_request")

    def test_priority_and_sla(self):
        ticket = self.manager.create_ticket("CFS-IT-2", "production down for all users", priority="critical")
        self.assertEqual(ticket.priority, "critical")
        self.assertEqual(ticket.sla_target_minutes, 60)

    def test_invalid_priority_is_safe(self):
        ticket = self.manager.create_ticket("CFS-IT-3", "help", priority="unknown")
        self.assertEqual(ticket.priority, "medium")

    def test_resolution_requires_verification(self):
        ticket = self.manager.create_ticket("CFS-IT-4", "printer error")
        self.manager.close_after_verification(ticket, verified=False)
        self.assertEqual(ticket.status, "open")
        self.manager.close_after_verification(ticket, verified=True)
        self.assertEqual(ticket.status, "resolved")

    def test_snapshot_is_safe(self):
        snapshot = self.manager.snapshot()
        self.assertTrue(snapshot["verification_before_resolution"])
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
