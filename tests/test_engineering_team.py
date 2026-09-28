import unittest

from src.core.engineering_team import EngineeringTeam


class EngineeringTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.team = EngineeringTeam()

    def test_specialists_exist(self) -> None:
        for agent_id in (
            "frontend_developer_agent", "backend_developer_agent", "full_stack_developer_agent",
            "mobile_developer_agent", "devops_platform_agent", "data_ai_engineer_agent",
            "game_interactive_agent", "qa_engineer_agent", "cybersecurity_developer_agent",
            "embedded_iot_agent", "engineering_supervisor_agent",
        ):
            self.assertTrue(self.team.exists(agent_id))

    def test_frontend_action_is_bounded(self) -> None:
        decision = self.team.authorize("frontend_developer_agent", "implement")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_approval)

    def test_deployment_requires_approval(self) -> None:
        decision = self.team.authorize("frontend_developer_agent", "publish")
        self.assertFalse(decision.allowed)
        deploy = self.team.get("engineering_supervisor_agent")["requires_approval_for"]
        self.assertIn("deploy", deploy)

    def test_unknown_action_is_denied(self) -> None:
        decision = self.team.authorize("backend_developer_agent", "delete_everything")
        self.assertFalse(decision.allowed)

    def test_capability_selection(self) -> None:
        self.assertEqual(self.team.select("rag"), "data_ai_engineer_agent")
        self.assertEqual(self.team.select("accessibility"), "qa_engineer_agent")

    def test_snapshot_is_credential_safe(self) -> None:
        snapshot = self.team.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertEqual(snapshot["default_action"], "deny")
        self.assertEqual(snapshot["production_access"], "gateway_only")


if __name__ == "__main__":
    unittest.main()
