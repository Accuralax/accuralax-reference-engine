from pathlib import Path

from src.core.event_automation import EventAutomation
from src.core.orchestration_plane import OrchestrationPlane


def test_event_dispatch_is_idempotent(tmp_path: Path):
    engine = EventAutomation(db_path=str(tmp_path / "events.sqlite3"))
    route = engine.define_route("t1", "w1", "invoice.created", "Invoice route", [
        {"action": "notify"}
    ])
    calls = []
    handlers = {"notify": lambda action, payload: calls.append(payload) or {"status": "completed"}}
    first = engine.dispatch("t1", "w1", "EV-1", "invoice.created", {"id": 1}, handlers)
    second = engine.dispatch("t1", "w1", "EV-1", "invoice.created", {"id": 1}, handlers)
    assert first["status"] == "completed"
    assert second["idempotent"] is True
    assert len(calls) == 1


def test_orchestration_create_is_idempotent(tmp_path: Path):
    plane = OrchestrationPlane(db_path=str(tmp_path / "orchestration.sqlite3"))
    first = plane.create("t1", "w1", "integration.dispatch", {}, requested_by="u1", correlation_id="CORR-1")
    second = plane.create("t1", "w1", "integration.dispatch", {}, requested_by="u1", correlation_id="CORR-1")
    assert first["run_id"] == second["run_id"]
    assert plane.health()["durable"] is True
