import unittest

from src.core.mcp_gateway import MCPGateway
from src.integrations.adapters.mock import build_mock_adapters
from src.integrations.execution import AuditedExecutor
from src.integrations.mcp_router import MCPIntegrationRouter


class MCPRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = MCPGateway()
        self.executor = AuditedExecutor()
        self.router = MCPIntegrationRouter(
            self.gateway, build_mock_adapters(), self.executor
        )

    def test_read_capability_reaches_adapter(self) -> None:
        result = self.router.execute("website", "read_form_submission", {"submission_id": "demo"})
        self.assertTrue(result["authorized"])
        self.assertEqual(result["status"], "succeeded")

    def test_denied_capability_never_reaches_adapter(self) -> None:
        result = self.router.execute("github", "delete_repository")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["status"], "denied")

    def test_side_effect_requires_idempotency_and_approval(self) -> None:
        self.gateway.data["systems"]["hubspot"]["actions"].append("create_contact")
        denied = self.router.execute("hubspot", "create_contact")
        self.assertFalse(denied["authorized"])
        self.assertEqual(denied["reason"], "idempotency_required")

        waiting = self.router.execute(
            "hubspot", "create_contact", approved=False, idempotency_key="contact-1"
        )
        self.assertFalse(waiting["authorized"])
        self.assertEqual(waiting["reason"], "human_approval_required")

    def test_approved_side_effect_is_audited(self) -> None:
        self.gateway.data["systems"]["hubspot"]["actions"].append("create_contact")
        result = self.router.execute(
            "hubspot", "create_contact", approved=True, idempotency_key="contact-2"
        )
        self.assertTrue(result["authorized"])
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("execution_id", result["receipt"])

    def test_snapshot_has_no_credentials(self) -> None:
        snapshot = self.gateway.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
