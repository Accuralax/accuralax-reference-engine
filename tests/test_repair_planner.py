import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from src.core.repair import RepairPlanner


class RepairPlannerTests(unittest.TestCase):
    def test_healthy_report_creates_no_repairs(self):
        report = {"status": "healthy", "checks": [{"name": "files", "status": "pass"}]}
        self.assertEqual(RepairPlanner().plan(report), [])

    def test_medium_issue_creates_bounded_plan_but_never_executes(self):
        report = {"status": "degraded", "checks": [{"name": "dependencies", "status": "fail"}]}
        plan = RepairPlanner().plan(report)[0]
        self.assertEqual(plan.risk, "medium")
        self.assertTrue(plan.requires_approval)
        self.assertTrue(plan.allowed)
        self.assertFalse(RepairPlanner().snapshot(report)["execution_enabled"])

    def test_security_guardrail_repair_is_blocked(self):
        report = {"status": "degraded", "checks": [{"name": "agent_permissions", "status": "fail"}]}
        plan = RepairPlanner().plan(report)[0]
        self.assertEqual(plan.risk, "high")
        self.assertFalse(plan.allowed)
        self.assertTrue(plan.requires_approval)


if __name__ == "__main__":
    unittest.main()
