import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from src.core.repair_graph import build_repair_graph


class RepairGraphTests(unittest.TestCase):
    def test_healthy_graph_reaches_terminal_state(self):
        graph = build_repair_graph()
        result = graph.invoke({"health_report": {"status": "healthy", "checks": [{"name": "files", "status": "pass"}]}})
        self.assertEqual(result["repair_status"], "healthy")
        self.assertEqual(result["iterations"], 1)

    def test_failure_stops_at_approval_gate(self):
        graph = build_repair_graph()
        result = graph.invoke({"health_report": {"status": "degraded", "checks": [{"name": "dependencies", "status": "fail"}]}})
        self.assertEqual(result["repair_status"], "awaiting_approval")
        self.assertEqual(len(result["plans"]), 1)

    def test_guardrail_failure_is_not_auto_approved(self):
        graph = build_repair_graph()
        result = graph.invoke({"health_report": {"status": "degraded", "checks": [{"name": "agent_permissions", "status": "fail"}]}})
        self.assertEqual(result["repair_status"], "awaiting_approval")
        self.assertFalse(result["plans"][0]["allowed"])


if __name__ == "__main__":
    unittest.main()
