import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import tempfile
import unittest
from src.core.repair_history import SQLiteRepairHistory


class RepairHistoryTests(unittest.TestCase):
    def test_event_survives_new_history_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "repairs.sqlite3"
            SQLiteRepairHistory(db).record("repair-x", "repair_failed", "failure", {"reason": "RuntimeError"})
            events = SQLiteRepairHistory(db).list("repair-x")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event, "repair_failed")

    def test_secret_fields_are_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = SQLiteRepairHistory(Path(tmp) / "repairs.sqlite3")
            history.record("repair-x", "attempt", "recorded", {"api_key": "DO_NOT_STORE", "reason": "test"})
            event = history.list("repair-x")[0]
            self.assertNotIn("api_key", event.details)
            self.assertNotIn("DO_NOT_STORE", str(event.details))

    def test_count_is_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "repairs.sqlite3"
            history = SQLiteRepairHistory(db)
            history.record("repair-a", "attempt", "allowed")
            history.record("repair-a", "repair_failed", "failure")
            self.assertEqual(SQLiteRepairHistory(db).count(), 2)


if __name__ == "__main__":
    unittest.main()
