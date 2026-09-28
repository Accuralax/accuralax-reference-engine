import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from src.core.health import HealthEngine


class HealthEngineTests(unittest.TestCase):
    def test_health_is_read_only_and_healthy(self):
        report = HealthEngine().run()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["score"], 100)
        self.assertTrue(all(item["status"] == "pass" for item in report["checks"]))

    def test_critical_guardrails_are_checked(self):
        report = HealthEngine().run()
        names = {item["name"] for item in report["checks"]}
        self.assertIn("agent_permissions", names)
        self.assertIn("business_gateway", names)
        self.assertIn("execution_ledger", names)


if __name__ == "__main__":
    unittest.main()
