import unittest

from src.core.data_platform_team import DataPlatformTeam, classify_platform_request, generate_domain_candidates


class DataPlatformTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.team = DataPlatformTeam()

    def test_core_specialists_exist(self) -> None:
        for agent in ("data_management_agent", "cloud_architecture_agent", "blockchain_web3_agent", "domain_identity_agent", "network_engineering_agent"):
            self.assertIsNotNone(self.team.get(agent))

    def test_capability_selection(self) -> None:
        self.assertEqual(self.team.select("rag"), None)
        self.assertEqual(self.team.select("cloud_architecture"), "cloud_architecture_agent")
        self.assertEqual(self.team.select("blockchain"), "blockchain_web3_agent")
        self.assertEqual(self.team.select("tcp_ip"), "network_engineering_agent")

    def test_domain_generation_is_non_destructive(self) -> None:
        candidates = generate_domain_candidates("Cyber Fusion")
        self.assertIn("cyberfusion.com", candidates)
        self.assertIn("cyberfusion.co.za", candidates)

    def test_domain_purchase_is_approval_gated(self) -> None:
        decision = self.team.authorize("domain_identity_agent", "domain_purchase")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")
        approved = self.team.authorize("domain_identity_agent", "domain_purchase", approved=True)
        self.assertTrue(approved.allowed)

    def test_cloud_deploy_is_approval_gated(self) -> None:
        decision = self.team.authorize("cloud_architecture_agent", "deploy")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")
        approved = self.team.authorize("cloud_architecture_agent", "deploy", approved=True)
        self.assertTrue(approved.allowed)

    def test_blockchain_transaction_is_approval_gated(self) -> None:
        decision = self.team.authorize("blockchain_web3_agent", "transaction")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")

    def test_network_change_is_approval_gated(self) -> None:
        decision = self.team.authorize("network_engineering_agent", "network_change")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "human_approval_required")

    def test_request_classification(self) -> None:
        self.assertEqual(classify_platform_request("design a cloud infrastructure"), "cloud_architecture")
        self.assertEqual(classify_platform_request("review blockchain smart contract"), "blockchain_web3")
        self.assertEqual(classify_platform_request("generate a domain and DNS plan"), "domain_identity")
        self.assertEqual(classify_platform_request("design a VLAN and VPN"), "network_engineering")

    def test_credential_safe_snapshot(self) -> None:
        snapshot = self.team.snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertEqual(snapshot["default_action"], "deny")


if __name__ == "__main__":
    unittest.main()
