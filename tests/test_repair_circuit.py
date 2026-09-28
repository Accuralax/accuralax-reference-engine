import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from src.core.repair_circuit import RepairCircuitBreaker


class RepairCircuitTests(unittest.TestCase):
    def test_repeated_failures_open_circuit(self):
        breaker = RepairCircuitBreaker(max_failures=2)
        self.assertTrue(breaker.allow("repair-files"))
        breaker.record_failure("repair-files", "test failure")
        self.assertTrue(breaker.allow("repair-files"))
        breaker.record_failure("repair-files", "test failure")
        self.assertFalse(breaker.allow("repair-files"))
        self.assertEqual(breaker.status("repair-files"), "open")

    def test_success_resets_failure_count(self):
        breaker = RepairCircuitBreaker(max_failures=2)
        breaker.record_failure("repair-files", "failure")
        breaker.record_success("repair-files")
        self.assertTrue(breaker.allow("repair-files"))
        self.assertEqual(breaker.status("repair-files"), "closed")

    def test_audit_log_records_lifecycle_without_secrets(self):
        breaker = RepairCircuitBreaker()
        breaker.record_failure("repair-x", "RuntimeError")
        events = breaker.audit_log("repair-x")
        self.assertTrue(events)
        self.assertEqual(events[-1].event, "repair_failed")
        self.assertNotIn("password", str(events))
        self.assertNotIn("api_key", str(events))


if __name__ == "__main__":
    unittest.main()
