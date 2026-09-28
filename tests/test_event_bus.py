from pathlib import Path
from src.core.event_bus import EventBus


def test_event_bus_persists_and_filters_secrets(tmp_path: Path):
    bus = EventBus(str(tmp_path / "events.sqlite3"))
    seen = []
    bus.subscribe("crm.client.created", seen.append)
    event = bus.publish(
        "crm.client.created", "t1", "w1", "agent", "client", "CLI-1", "ref-1",
        {"name": "Client", "token": "hidden", "nested": {"api_key": "hidden"}},
        idempotency_key="client-1",
    )
    assert event.payload == {"name": "Client", "nested": {}}
    assert seen and seen[0].event_id == event.event_id
    assert len(bus.history("t1", "w1", entity_id="CLI-1")) == 1


def test_event_bus_idempotency_and_scope(tmp_path: Path):
    bus = EventBus(str(tmp_path / "events.sqlite3"))
    first = bus.publish("lms.enrolment.created", "t1", "w1", "agent", "learner", "L1", "r1",
                        {"course_id": "C1"}, idempotency_key="enrol-1")
    second = bus.publish("lms.enrolment.created", "t1", "w1", "agent", "learner", "L1", "r2",
                         {"course_id": "C2"}, idempotency_key="enrol-1")
    assert first.event_id == second.event_id
    bus.publish("lms.enrolment.created", "t2", "w2", "agent", "learner", "L1", "r3", {"course_id": "C3"},
                idempotency_key="enrol-1")
    assert len(bus.history("t1", "w1")) == 1
    assert len(bus.history("t2", "w2")) == 1


def test_event_bus_replay(tmp_path: Path):
    bus = EventBus(str(tmp_path / "events.sqlite3"))
    bus.publish("sales.lead.created", "t1", "w1", "agent", "lead", "L1", "r1", {"score": 80})
    bus.publish("sales.lead.qualified", "t1", "w1", "agent", "lead", "L1", "r2", {"score": 90})
    replayed = []
    assert bus.replay("t1", "w1", replayed.append, entity_id="L1") == 2
    assert [x.event_type for x in replayed] == ["sales.lead.created", "sales.lead.qualified"]
