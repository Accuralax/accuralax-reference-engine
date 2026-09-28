import unittest
from datetime import datetime, timezone, timedelta

from src.core.it_sla import ITSLAManager


class ITSLATests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ITSLAManager()
        self.created = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)

    def test_deadline_uses_priority_target(self):
        case = self.manager.create_case("IT-1", "high", created_at=self.created)
        self.assertEqual(self.manager.deadline(case), self.created + timedelta(minutes=240))

    def test_case_is_within_sla(self):
        case = self.manager.create_case("IT-2", "medium", created_at=self.created)
        result = self.manager.status(case, now=self.created + timedelta(minutes=30))
        self.assertEqual(result["state"], "within_sla")
        self.assertFalse(result["breached"])

    def test_case_becomes_at_risk(self):
        case = self.manager.create_case("IT-3", "medium", created_at=self.created)
        result = self.manager.status(case, now=self.created + timedelta(minutes=390))
        self.assertEqual(result["state"], "at_risk")

    def test_breach_triggers_escalation(self):
        case = self.manager.create_case("IT-4", "critical", created_at=self.created)
        now = self.created + timedelta(minutes=61)
        self.assertEqual(self.manager.status(case, now=now)["state"], "breached")
        result = self.manager.escalate_if_needed(case, now=now)
        self.assertTrue(result["escalation_required"])
        self.assertEqual(result["reason"], "sla_breached")

    def test_resolution_stops_breach(self):
        case = self.manager.create_case("IT-5", "high", created_at=self.created)
        self.manager.resolve(case, at=self.created + timedelta(minutes=120))
        result = self.manager.status(case, now=self.created + timedelta(minutes=300))
        self.assertEqual(result["state"], "resolved")

    def test_invalid_priority_falls_back_safely(self):
        case = self.manager.create_case("IT-6", "unknown", created_at=self.created)
        self.assertEqual(case.priority, "medium")

    def test_snapshot_has_no_external_side_effects(self):
        snapshot = self.manager.snapshot()
        self.assertFalse(snapshot["automatic_external_side_effects"])


if __name__ == "__main__":
    unittest.main()
