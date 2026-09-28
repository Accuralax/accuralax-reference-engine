import unittest
from pathlib import Path

from src.core.gateway import AgentGateway
from src.core.orchestrator import ConversationOrchestrator
from src.core.session_store import InMemoryConversationStore, SQLiteConversationStore


class SessionAndGatewayTests(unittest.TestCase):
    def test_sqlite_busy_timeout(self) -> None:
        with __import__("tempfile").TemporaryDirectory() as directory:
            store = SQLiteConversationStore(Path(directory) / "sessions.sqlite3")
            conn = store._connect()
            try:
                self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 15000)
            finally:
                conn.close()

    def test_sqlite_session_survives_new_orchestrator(self) -> None:
        db = Path(self.id().replace(".", "_") + ".sqlite3")
        try:
            first = ConversationOrchestrator(SQLiteConversationStore(db))
            started = first.start("I want to register my business")

            second = ConversationOrchestrator(SQLiteConversationStore(db))
            loaded = second.get(started.state.reference_id)

            self.assertEqual(loaded.state.service_id, "business_registration")
            self.assertEqual(loaded.state.reference_id, started.state.reference_id)
        finally:
            db.unlink(missing_ok=True)

    def test_sensitive_fields_are_not_persisted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteConversationStore(Path(directory) / "sessions.sqlite3")
            state = ConversationOrchestrator(store).start("I need cybersecurity help").state
            state.collected["api_key"] = "should-never-persist"

            with self.assertRaises(ValueError):
                store.save(state)

    def test_gateway_supports_multi_turn_boundary(self) -> None:
        gateway = AgentGateway(ConversationOrchestrator(InMemoryConversationStore()))
        started = gateway.handle({"action": "start", "message": "I want to register my business"})

        self.assertEqual(started["status"], "information_required")
        reference_id = started["reference_id"]
        next_field = started["missing_information"][0]

        updated = gateway.handle({
            "action": "information",
            "reference_id": reference_id,
            "field": next_field,
            "value": "CyberFusion Demo",
        })

        self.assertEqual(updated["reference_id"], reference_id)
        self.assertEqual(updated["status"], "information_required")

    def test_gateway_rejects_unknown_action(self) -> None:
        gateway = AgentGateway()
        with self.assertRaises(ValueError):
            gateway.handle({"action": "explode"})


if __name__ == "__main__":
    unittest.main()
