import unittest

from src.core.domain_supervisors import DomainSupervisor, DomainSupervisorRegistry


class DomainSupervisorTests(unittest.TestCase):
    def test_all_domains_exist(self):
        registry = DomainSupervisorRegistry()
        self.assertEqual(
            sorted(registry.snapshot()["domains"]),
            ["business", "cybersecurity", "data_platform", "engineering", "it"],
        )

    def test_engineering_delegation(self):
        supervisor = DomainSupervisor("engineering")
        decision = supervisor.delegate("backend_developer_agent")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.supervisor, "engineering_supervisor_agent")

    def test_unknown_specialist_is_denied(self):
        supervisor = DomainSupervisor("it")
        decision = supervisor.delegate("backend_developer_agent")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "specialist_not_allowed")

    def test_delegation_limit(self):
        supervisor = DomainSupervisor("it")
        decision = supervisor.delegate("it_support_agent", delegation_count=6)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "delegation_limit")

    def test_sensitive_action_requires_approval(self):
        supervisor = DomainSupervisor("engineering")
        decision = supervisor.delegate("devops_platform_agent", action="deploy", approved=False)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)

    def test_approved_sensitive_action_is_allowed(self):
        supervisor = DomainSupervisor("engineering")
        decision = supervisor.delegate("devops_platform_agent", action="deploy", approved=True)
        self.assertTrue(decision.allowed)

    def test_snapshot_is_credential_safe(self):
        snapshot = DomainSupervisor("cybersecurity").snapshot()
        self.assertFalse(snapshot["credentials_exposed_to_agents"])
        self.assertEqual(snapshot["production_access"], "gateway_only")


if __name__ == "__main__":
    unittest.main()
