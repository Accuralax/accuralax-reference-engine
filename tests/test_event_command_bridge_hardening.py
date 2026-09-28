from pathlib import Path

from src.core.enterprise_command_control import EnterpriseCommandControl
from src.core.event_bus import EventBus
from src.core.event_command_bridge import EventCommandBridge
from src.core.operational_execution import OperationalExecution
from src.core.task_assignment import TaskAssignment


def test_bridge_is_durable_scoped_and_idempotent(tmp_path: Path):
    bus = EventBus(str(tmp_path / "events.sqlite3"))
    control = EnterpriseCommandControl(db_path=str(tmp_path / "commands.sqlite3"))
    tasks = TaskAssignment(db_path=str(tmp_path / "tasks.sqlite3"))
    operational = OperationalExecution(tasks, db_path=str(tmp_path / "ops.sqlite3"))
    bridge = EventCommandBridge(
        bus, control, operational_execution=operational,
        db_path=str(tmp_path / "bridge.sqlite3"),
    )
    event = bus.publish(
        "task.requested", "t1", "w1", "u1", "task", "task-1", "ref-1",
        {"task_title": "Bridge work", "correlation_id": "corr-1"},
        trace_id="trace-1",
        idempotency_key="evt-1",
    )
    first = bridge.handle(event)
    second = bridge.handle(event)

    assert first["command_id"]
    assert first["command_status"] == "authorized"
    assert first["operational"]["status"] == "completed"
    assert second["event_id"] == event.event_id
    assert len(operational.history("t1", "w1")) == 1
    assert len(bridge.history("t1", "w1")) == 1
    assert bridge.health()["idempotent"] is True


def test_bridge_uses_governance_for_high_risk_events(tmp_path: Path):
    bus = EventBus(str(tmp_path / "events.sqlite3"))
    control = EnterpriseCommandControl(db_path=str(tmp_path / "commands.sqlite3"))
    bridge = EventCommandBridge(bus, control, db_path=str(tmp_path / "bridge.sqlite3"))

    event = bus.publish(
        "security.action.requested", "t1", "w1", "u1", "security", "sec-1", "ref-1",
        {"action": "rotate-secret"},
        trace_id="trace-sec",
        idempotency_key="sec-1",
    )
    result = bridge.handle(event)

    assert result["command_status"] == "awaiting_approval"
    assert result["executed"] is False
    command = control.get("t1", "w1", result["command_id"])
    assert command["status"] == "awaiting_approval"
