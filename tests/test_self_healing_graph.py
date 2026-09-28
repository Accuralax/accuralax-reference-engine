import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from src.core.self_healing_graph import build_self_healing_graph


class SelfHealingGraphTests(unittest.TestCase):
    def test_healthy_path(self):
        result = build_self_healing_graph().invoke({"health_report": {"status": "healthy", "checks": []}})
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["verification_ok"])

    def test_failed_dependency_stops_for_approval(self):
        result = build_self_healing_graph().invoke({"health_report": {"status": "degraded", "checks": [{"name": "dependencies", "status": "fail"}]}})
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertFalse(result["apply_ok"] if "apply_ok" in result else False)

    def test_policy_failure_is_blocked(self):
        result = build_self_healing_graph().invoke({"health_report": {"status": "degraded", "checks": [{"name": "agent_permissions", "status": "fail"}]}, "approved": True})
        self.assertEqual(result["status"], "blocked_policy")

    def test_approved_repair_cannot_bypass_controlled_apply(self):
        result = build_self_healing_graph().invoke({"health_report": {"status": "degraded", "checks": [{"name": "dependencies", "status": "fail"}]}, "approved": True})
        self.assertEqual(result["status"], "awaiting_controlled_apply")
        self.assertFalse(result["apply_ok"])


if __name__ == "__main__":
    unittest.main()
