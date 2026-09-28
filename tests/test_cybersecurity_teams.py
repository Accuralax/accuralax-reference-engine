import unittest

from src.core.cybersecurity_teams import CybersecurityTeamEngine


class CybersecurityTeamsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CybersecurityTeamEngine()

    def test_scope_is_required(self) -> None:
        result = self.engine.authorize(
            "red_team", "attack_path_simulation", authorized_scope=False
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "authorized_scope_required")

    def test_red_team_allows_bounded_validation(self) -> None:
        result = self.engine.authorize(
            "red_team", "attack_path_simulation", authorized_scope=True
        )
        self.assertTrue(result.allowed)

    def test_red_team_rejects_unknown_mode(self) -> None:
        result = self.engine.authorize(
            "red_team", "unknown_mode", authorized_scope=True
        )
        self.assertFalse(result.allowed)

    def test_blue_team_is_defensive(self) -> None:
        result = self.engine.authorize(
            "blue_team", "hardening", authorized_scope=True
        )
        self.assertTrue(result.allowed)

    def test_blue_team_rejects_unknown_mode(self) -> None:
        result = self.engine.authorize(
            "blue_team", "unknown_mode", authorized_scope=True
        )
        self.assertFalse(result.allowed)
    def test_product_release_requires_approval(self) -> None:
        result = self.engine.authorize(
            "security_product_team", "package", authorized_scope=True
        )
        self.assertTrue(result.allowed)
        self.assertTrue(result.requires_approval)

    def test_finding_becomes_defensive_product(self) -> None:
        product = self.engine.product_opportunity({"category": "identity"})
        self.assertIsNotNone(product)
        self.assertIn("least-privilege", product.controls)

    def test_unknown_finding_has_no_product(self) -> None:
        product = self.engine.product_opportunity({"category": "unknown"})
        self.assertIsNone(product)

    def test_snapshot_exposes_no_credentials(self) -> None:
        snapshot = self.engine.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
