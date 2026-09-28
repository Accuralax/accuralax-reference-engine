import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from src.core.agent_permissions import AgentPermissionRegistry
from src.core.supervisor import AgentSupervisor

class AgentAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentPermissionRegistry()
        self.supervisor = AgentSupervisor(self.registry)
    def test_specialist_selection(self):
        self.assertEqual(self.supervisor.select_specialist("cybersecurity"), "cybersecurity_triage_agent")
        self.assertEqual(self.supervisor.select_specialist("ai_automation"), "ai_automation_agent")
    def test_tools_default_to_deny(self):
        self.assertFalse(self.registry.can_use_tool("cybersecurity_triage_agent", "shell"))
    def test_skill_scope_is_enforced(self):
        self.assertTrue(self.registry.can_use_skill("cybersecurity_triage_agent", "cybersecurity_triage"))
        self.assertFalse(self.registry.can_use_skill("business_operations_agent", "cybersecurity_triage"))
    def test_delegation_is_bounded(self):
        self.assertTrue(self.supervisor.authorize_delegation("cybersecurity_triage_agent", "digital_agent", 0).allowed)
        self.assertFalse(self.supervisor.authorize_delegation("cybersecurity_triage_agent", "digital_agent", 2).allowed)
    def test_repair_cannot_be_delegated(self):
        decision = self.supervisor.authorize_delegation("cybersecurity_triage_agent", "repair_agent", 0)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "repair_requires_human_approval")
