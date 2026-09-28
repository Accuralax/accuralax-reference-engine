import unittest

from src.core.domain_supervisor_graph import run_domain_supervisor_graph


class DomainSupervisorGraphTests(unittest.TestCase):
    def test_engineering_reaches_specialist(self):
        state = run_domain_supervisor_graph("engineering", "backend_developer_agent")
        self.assertEqual(state["status"], "ready_for_specialist")
        self.assertEqual(state["verification_status"], "pass")
        self.assertIn("domain_gate", state["history"])

    def test_unknown_domain_stops(self):
        state = run_domain_supervisor_graph("unknown", "backend_developer_agent")
        self.assertEqual(state["status"], "unknown_domain")
        self.assertTrue(state["terminal"])

    def test_unknown_specialist_stops(self):
        state = run_domain_supervisor_graph("it", "backend_developer_agent")
        self.assertEqual(state["status"], "specialist_not_allowed")

    def test_deploy_waits_for_approval(self):
        state = run_domain_supervisor_graph(
            "engineering",
            "devops_platform_agent",
            action="deploy",
            approved=False,
        )
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertFalse(state["terminal"])

    def test_approved_deploy_reaches_specialist(self):
        state = run_domain_supervisor_graph(
            "engineering",
            "devops_platform_agent",
            action="deploy",
            approved=True,
        )
        self.assertEqual(state["status"], "ready_for_specialist")

    def test_delegation_limit_stops(self):
        state = run_domain_supervisor_graph(
            "it",
            "it_support_agent",
            max_delegations=0,
        )
        self.assertEqual(state["status"], "delegation_limit")

    def test_credentials_never_exposed(self):
        state = run_domain_supervisor_graph("cybersecurity", "security_blue_agent")
        self.assertFalse(state["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
