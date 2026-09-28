import tempfile
import unittest
from pathlib import Path

from src.core.it_durable_event_bus import DurableITEventBus
from src.core.it_persistent_store import ITPersistentStore


class DurableITEventBusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        store = ITPersistentStore(Path(self.tmp.name) / "events.sqlite3")
        self.bus = DurableITEventBus(event_store=store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_publish_persists_event(self):
        event = self.bus.publish("ticket_created", "CFS-IT-300", ticket_id="IT-300", payload={"priority": "high"})
        rows = self.bus.durable_history("CFS-IT-300", ticket_id="IT-300")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "ticket_created")
        self.assertEqual(rows[0]["details"]["event_id"], event.event_id)

    def test_event_survives_new_bus_instance(self):
        self.bus.publish("sla_breach", "CFS-IT-301", ticket_id="IT-301", payload={"priority": "critical"})
        second = DurableITEventBus(event_store=ITPersistentStore(self.bus.event_store.path))
        rows = second.durable_history("CFS-IT-301")
        self.assertEqual(len(rows), 1)

    def test_replay_dispatches_to_handler(self):
        self.bus.publish("asset_linked", "CFS-IT-302", ticket_id="IT-302", payload={"asset_id": "AST-1"})
        second = DurableITEventBus(event_store=ITPersistentStore(self.bus.event_store.path))
        received = []
        second.subscribe("asset_linked", received.append)
        replayed = second.replay("CFS-IT-302")
        self.assertEqual(len(replayed), 1)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].event_type, "asset_linked")

    def test_replay_can_filter_event_types(self):
        self.bus.publish("a", "CFS-IT-303")
        self.bus.publish("b", "CFS-IT-303")
        second = DurableITEventBus(event_store=ITPersistentStore(self.bus.event_store.path))
        replayed = second.replay("CFS-IT-303", event_types={"b"})
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].event_type, "b")

    def test_snapshot_is_durable_and_safe(self):
        snapshot = self.bus.snapshot()
        self.assertTrue(snapshot["durable"])
        self.assertTrue(snapshot["replay_supported"])
        self.assertFalse(snapshot["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
