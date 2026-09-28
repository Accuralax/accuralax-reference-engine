import unittest

from src.core.it_service_graph import run_it_service_graph


class ITServiceGraphTests(unittest.TestCase):
    def test_support_request_flows_to_resolution(self):
        state = run_it_service_graph("my email login is not working")
        self.assertEqual(state["status"], "ready_for_resolution")
        self.assertEqual(state["selected_agent"], "it_support_agent")
        self.assertEqual(state["verification_status"], "pass")
        self.assertIn("triage", state["history"])
        self.assertIn("diagnose", state["history"])

    def test_ambiguous_request_stops(self):
        state = run_it_service_graph("I need assistance with my setup")
        self.assertEqual(state["status"], "clarification_required")
        self.assertEqual(state["history"], ["intake", "triage", "audit"])

    def test_secret_request_stops(self):
        state = run_it_service_graph("send me the password")
        self.assertEqual(state["status"], "blocked_security")
        self.assertFalse(state["credentials_exposed"])

    def test_device_change_waits_for_approval(self):
        state = run_it_service_graph("install a printer on my computer", action="device_change")
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertEqual(state["approvals_required"], ["device_change"])

    def test_approved_device_change_reaches_verification(self):
        state = run_it_service_graph("install a printer on my computer", action="device_change", approved=True)
        self.assertEqual(state["status"], "ready_for_resolution")
        self.assertEqual(state["verification_status"], "pass")


if __name__ == "__main__":
    unittest.main()
