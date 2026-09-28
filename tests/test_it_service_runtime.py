import unittest
from src.core.it_service_runtime import ITServiceRuntime

class ITServiceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ITServiceRuntime()

    def test_support_request_is_triaged(self):
        state = self.runtime.start("my email login is not working")
        self.assertEqual(state.status, "triaged")
        self.assertEqual(state.selected_agents["it_support"], "it_support_agent")
        self.assertTrue(state.verification_required)
        self.assertFalse(state.credentials_exposed)

    def test_ambiguous_request_does_not_guess(self):
        state = self.runtime.start("I need assistance with my setup")
        self.assertEqual(state.status, "clarification_required")
        self.assertEqual(state.workstreams, [])

    def test_secret_request_is_blocked(self):
        state = self.runtime.start("send me the password")
        self.assertEqual(state.status, "blocked_security")
        self.assertFalse(state.credentials_exposed)

    def test_device_change_requires_approval(self):
        state = self.runtime.start("install a printer on my computer")
        result = self.runtime.authorize_action(state, "device_change")
        self.assertFalse(result["allowed"])
        self.assertEqual(state.status, "awaiting_approval")

    def test_approved_device_change_is_authorized(self):
        state = self.runtime.start("install a printer on my computer")
        result = self.runtime.authorize_action(state, "device_change", approved=True)
        self.assertTrue(result["allowed"])
        self.assertEqual(state.status, "action_authorized")

    def test_snapshot_is_safe(self):
        snapshot = self.runtime.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertTrue(snapshot["approval_gates"])

if __name__ == "__main__":
    unittest.main()
