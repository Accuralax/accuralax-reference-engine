import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import unittest
from src.core.full_healing_graph import build_full_healing_graph

class FullHealingGraphTests(unittest.TestCase):
    def test_healthy_cycle(self):
        r=build_full_healing_graph().invoke({"health_report":{"status":"healthy","checks":[]}})
        self.assertEqual(r["status"],"healthy")
        self.assertTrue(r["verification_ok"])

    def test_degraded_stops_for_approval(self):
        r=build_full_healing_graph().invoke({"health_report":{"status":"degraded","checks":[{"name":"dependencies","status":"fail"}]}})
        self.assertEqual(r["status"],"awaiting_approval")

    def test_approved_still_requires_concrete_candidate(self):
        r=build_full_healing_graph().invoke({"health_report":{"status":"degraded","checks":[{"name":"dependencies","status":"fail"}]},"approved":True})
        self.assertEqual(r["status"],"awaiting_repair_candidate")
        self.assertFalse(r["execution"]["ok"])

    def test_high_risk_cannot_execute(self):
        r=build_full_healing_graph().invoke({"health_report":{"status":"degraded","checks":[{"name":"agent_permissions","status":"fail"}]},"approved":True})
        self.assertEqual(r["status"],"blocked_verification")

if __name__ == "__main__": unittest.main()
