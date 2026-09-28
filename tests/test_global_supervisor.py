import unittest

from src.core.global_supervisor import GlobalSupervisor


class GlobalSupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.supervisor = GlobalSupervisor()

    def test_routes_it(self):
        route = self.supervisor.route("My laptop is not working")
        self.assertTrue(route.allowed)
        self.assertEqual(route.domain, "it")

    def test_routes_engineering(self):
        route = self.supervisor.route("Build a backend API")
        self.assertTrue(route.allowed)
        self.assertEqual(route.domain, "engineering")

    def test_routes_data_platform(self):
        route = self.supervisor.route("Design our cloud architecture")
        self.assertTrue(route.allowed)
        self.assertEqual(route.domain, "data_platform")

    def test_routes_cybersecurity(self):
        route = self.supervisor.route("We have a cybersecurity incident")
        self.assertTrue(route.allowed)
        self.assertEqual(route.domain, "cybersecurity")

    def test_ambiguous_request_is_not_guessed(self):
        route = self.supervisor.route("I need help")
        self.assertFalse(route.allowed)
        self.assertEqual(route.reason, "clarification_required")

    def test_it_action_uses_specialist_policy(self):
        route = self.supervisor.route("I need a laptop device change")
        decision = self.supervisor.authorize_domain_action(
            route.domain, route.specialist, "device_change", approved=False
        )
        self.assertFalse(decision["allowed"])
        self.assertTrue(decision["requires_approval"])

    def test_snapshot_is_credential_safe(self):
        snapshot = self.supervisor.snapshot()
        self.assertTrue(snapshot["bounded"])
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertEqual(snapshot["default_action"], "deny")


if __name__ == "__main__":
    unittest.main()
