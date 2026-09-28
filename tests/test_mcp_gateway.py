import unittest

from src.core.mcp_gateway import MCPGateway


class MCPGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = MCPGateway()

    def test_unknown_system_denied(self) -> None:
        decision = self.gateway.authorize("unknown", "read_repository")
        self.assertFalse(decision.allowed)

    def test_read_action_allowed(self) -> None:
        decision = self.gateway.authorize("github", "read_repository")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.side_effect)

    def test_undeclared_action_denied(self) -> None:
        decision = self.gateway.authorize("github", "delete_repository")
        self.assertFalse(decision.allowed)

    def test_write_requires_idempotency(self) -> None:
        decision = self.gateway.authorize("github", "read_issue", approved=True)
        self.assertTrue(decision.allowed)

    def test_snapshot_is_credential_safe(self) -> None:
        snapshot = self.gateway.snapshot()
        self.assertEqual(snapshot["default_action"], "deny")
        self.assertEqual(snapshot["default_mode"], "read_only")
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
