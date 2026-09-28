import tempfile
import unittest
from pathlib import Path

from src.core.it_operational_store import ITOperationalStore
from src.core.it_service_graph_v2 import run_persistent_it_graph


class PersistentITGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ITOperationalStore(Path(self.tmp.name) / "ops.sqlite3")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_request_is_persisted(self):
        state = run_persistent_it_graph(
            "My laptop is not working",
            reference_id="CFS-IT-200",
            store=self.store,
        )
        self.assertTrue(state["ticket_id"].startswith("IT-"))
        self.assertIn("open_or_resume", state["history"])
        self.assertFalse(state["resumed"])

    def test_existing_ticket_is_resumed(self):
        first = run_persistent_it_graph(
            "Printer is not working",
            reference_id="CFS-IT-201",
            store=self.store,
        )
        ticket_id = first["ticket_id"]
        second_store = ITOperationalStore(self.store.path)
        resumed = run_persistent_it_graph(ticket_id=ticket_id, store=second_store)
        self.assertTrue(resumed["resumed"])
        self.assertEqual(resumed["ticket_id"], ticket_id)
        self.assertIn("load", resumed["history"])

    def test_ambiguous_request_is_blocked(self):
        state = run_persistent_it_graph(
            "I need assistance",
            reference_id="CFS-IT-202",
            store=self.store,
        )
        self.assertEqual(state["status"], "classification_required")

    def test_secret_request_is_blocked(self):
        state = run_persistent_it_graph(
            "Please send the password",
            reference_id="CFS-IT-203",
            store=self.store,
        )
        self.assertEqual(state["status"], "secret_request_blocked")
        self.assertFalse(state["credentials_exposed"])

    def test_action_approval_gate(self):
        state = run_persistent_it_graph(
            "I need a computer configuration change",
            reference_id="CFS-IT-204",
            action="configuration_change",
            approved=False,
            store=self.store,
        )
        self.assertEqual(state["status"], "awaiting_approval")

    def test_approved_action_reaches_verification(self):
        state = run_persistent_it_graph(
            "I need a computer configuration change",
            reference_id="CFS-IT-205",
            action="configuration_change",
            approved=True,
            store=self.store,
        )
        self.assertEqual(state["status"], "ready_for_resolution")
        self.assertEqual(state["verification_status"], "pass")


if __name__ == "__main__":
    unittest.main()
