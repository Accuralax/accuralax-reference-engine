import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import tempfile
import unittest
from src.core.self_healing import SelfHealingOrchestrator


class SelfHealingOrchestratorTests(unittest.TestCase):
    def test_healthy_report_does_not_create_repairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = SelfHealingOrchestrator(str(Path(tmp)), str(Path(tmp) / "repairs.sqlite3")).run({
                "status": "healthy", "checks": [{"name": "files", "status": "pass"}]
            })
            self.assertEqual(result.status, "healthy")
            self.assertEqual(result.repair_count, 0)

    def test_failed_dependency_becomes_approval_ready_not_auto_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = SelfHealingOrchestrator(str(Path(tmp)), str(Path(tmp) / "repairs.sqlite3")).run({
                "status": "degraded", "checks": [{"name": "dependencies", "status": "fail"}]
            })
            self.assertEqual(result.status, "repair_review_required")
            self.assertEqual(result.repair_count, 1)
            self.assertEqual(result.blocked_count, 0)
            self.assertGreaterEqual(result.audit_events, 2)

    def test_guardrail_failure_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = SelfHealingOrchestrator(str(Path(tmp)), str(Path(tmp) / "repairs.sqlite3")).run({
                "status": "degraded", "checks": [{"name": "agent_permissions", "status": "fail"}]
            })
            self.assertEqual(result.blocked_count, 1)
            self.assertEqual(result.circuit_open_count, 0)


if __name__ == "__main__":
    unittest.main()
