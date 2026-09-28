import tempfile
import unittest
from pathlib import Path

from src.core.it_persistent_store import ITPersistentStore


class ITPersistentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ITPersistentStore(Path(self.tmp.name) / "it.sqlite3")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_event_survives_new_store_instance(self):
        self.store.record("CFS-IT-1", "ticket_created", {"ticket_id": "IT-1"})
        second = ITPersistentStore(self.store.path)
        events = second.list_events("CFS-IT-1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "ticket_created")

    def test_ticket_filter(self):
        self.store.record("CFS-IT-2", "ticket_created", {}, ticket_id="IT-2")
        self.store.record("CFS-IT-2", "asset_linked", {}, ticket_id="IT-2")
        self.store.record("CFS-IT-2", "other", {}, ticket_id="IT-3")
        events = self.store.list_events("CFS-IT-2", ticket_id="IT-2")
        self.assertEqual(len(events), 2)

    def test_secrets_are_filtered(self):
        self.store.record(
            "CFS-IT-3",
            "safe_event",
            {"password": "hidden", "token": "hidden", "visible": "ok"},
        )
        event = self.store.list_events("CFS-IT-3")[0]
        self.assertNotIn("password", event["details"])
        self.assertNotIn("token", event["details"])
        self.assertEqual(event["details"]["visible"], "ok")

    def test_count(self):
        self.store.record("CFS-IT-4", "one")
        self.store.record("CFS-IT-5", "two")
        self.assertEqual(self.store.count(), 2)


if __name__ == "__main__":
    unittest.main()
