import unittest

from src.core.it_event_bus import ITEventBus


class ITEventBusTests(unittest.TestCase):
    def test_publish_and_subscribe(self):
        bus = ITEventBus()
        received = []
        bus.subscribe("ticket_created", received.append)
        event = bus.publish("ticket_created", "CFS-IT-1", ticket_id="IT-1", payload={"priority": "high"})
        self.assertEqual(received[0].event_id, event.event_id)
        self.assertEqual(bus.history(ticket_id="IT-1")[0].event_type, "ticket_created")

    def test_secrets_are_filtered(self):
        bus = ITEventBus()
        event = bus.publish(
            "safe",
            "CFS-IT-2",
            payload={"password": "hidden", "token": "hidden", "ok": "yes"},
        )
        self.assertNotIn("password", event.payload)
        self.assertNotIn("token", event.payload)
        self.assertEqual(event.payload["ok"], "yes")

    def test_handler_limit_is_bounded(self):
        bus = ITEventBus(max_handlers_per_event=1)
        bus.subscribe("event", lambda _: None)
        with self.assertRaises(ValueError):
            bus.subscribe("event", lambda _: None)

    def test_history_filters(self):
        bus = ITEventBus()
        bus.publish("a", "CFS-IT-3", ticket_id="IT-3")
        bus.publish("b", "CFS-IT-3", ticket_id="IT-4")
        self.assertEqual(len(bus.history(reference_id="CFS-IT-3")), 2)
        self.assertEqual(len(bus.history(ticket_id="IT-4")), 1)

    def test_snapshot_is_safe(self):
        snapshot = ITEventBus().snapshot()
        self.assertFalse(snapshot["credentials_exposed"])
        self.assertEqual(snapshot["external_side_effects"], "handlers_must_use_gateway")


if __name__ == "__main__":
    unittest.main()
