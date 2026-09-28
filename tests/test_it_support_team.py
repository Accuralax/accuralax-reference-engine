import unittest

from src.core.it_support_team import ITSupportTeam, classify_it_request, contains_secret_request


class ITSupportTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.team = ITSupportTeam()

    def test_core_agents_exist(self) -> None:
        for agent in ("it_support_agent", "it_technician_agent", "ict_agent", "mis_agent", "it_service_supervisor_agent"):
            self.assertIsNotNone(self.team.get(agent))

    def test_capability_selection(self) -> None:
        self.assertEqual(self.team.select("helpdesk"), "it_support_agent")
        self.assertEqual(self.team.select("hardware"), "it_technician_agent")
        self.assertEqual(self.team.select("ict"), "ict_agent")
        self.assertEqual(self.team.select("mis"), "mis_agent")

    def test_support_ticket_is_allowed(self) -> None:
        decision = self.team.authorize("it_support_agent", "create_ticket")
        self.assertTrue(decision.allowed)

    def test_device_change_requires_approval(self) -> None:
        decision = self.team.authorize("it_technician_agent", "device_change")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")
        approved = self.team.authorize("it_technician_agent", "device_change", approved=True)
        self.assertTrue(approved.allowed)

    def test_ict_infrastructure_change_requires_approval(self) -> None:
        decision = self.team.authorize("ict_agent", "infrastructure_change")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")

    def test_mis_data_change_requires_approval(self) -> None:
        decision = self.team.authorize("mis_agent", "data_change")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")

    def test_unknown_action_denied(self) -> None:
        decision = self.team.authorize("it_support_agent", "delete_everything")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "action_not_allowed")

    def test_classification(self) -> None:
        self.assertEqual(classify_it_request("my email login is not working"), "it_support")
        self.assertEqual(classify_it_request("install a printer on my computer"), "it_technician")
        self.assertEqual(classify_it_request("design office wifi connectivity"), "ict")
        self.assertEqual(classify_it_request("build a management dashboard report"), "mis")

    def test_secret_request_detection(self) -> None:
        self.assertTrue(contains_secret_request("please send me your password"))
        self.assertFalse(contains_secret_request("my printer is offline"))

    def test_snapshot_is_credential_safe(self) -> None:
        snapshot = self.team.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertEqual(snapshot["default_action"], "deny")
        self.assertEqual(snapshot["provider_access"], "gateway_only")


if __name__ == "__main__":
    unittest.main()
