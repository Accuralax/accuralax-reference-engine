import tempfile
from pathlib import Path
from src.core.approval_execution_gate import ApprovalExecutionGate
from src.core.enterprise_command_control import EnterpriseCommandControl
from src.core.event_command_bridge import EventCommandBridge
from src.core.event_bus import EventBus
from src.core.task_assignment import TaskAssignment
from src.core.workflow_automation import WorkflowAutomation
from src.core.operational_execution import OperationalExecution


class FakeOperational:
    def __init__(self):
        self.calls = []

    def execute_event(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"status": "completed", "run_id": "OP-1"}


def test_high_risk_event_waits_then_approves_and_resumes():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        events = EventBus(str(root / "events.sqlite3"))
        gate = ApprovalExecutionGate(db_path=str(root / "approval.sqlite3"))
        control = EnterpriseCommandControl(approval_gate=gate, db_path=str(root / "commands.sqlite3"))
        operational = FakeOperational()
        bridge = EventCommandBridge(events, control, operational, db_path=str(root / "bridge.sqlite3"))

        event = events.publish(
            "security.action.requested", "t1", "w1", "u1", "security", "s1", "s1",
            {"action": "contain", "risk": "high"}, trace_id="trace-1"
        )
        result = bridge.handle(event)
        assert result["command_status"] == "awaiting_approval"
        assert result["executed"] is False
        command_id = result["command_id"]
        assert gate.history("t1", "w1")[0]["status"] == "pending_approval"

        resumed = bridge.approve_and_resume("t1", "w1", command_id, "approver-1", True, "reviewed")
        assert resumed["status"] == "completed"
        assert resumed["executed"] is True
        assert len(operational.calls) == 1
        assert gate.history("t1", "w1")[0]["status"] == "approved"


def test_low_risk_event_is_authorized_without_pending_approval():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        events = EventBus(str(root / "events.sqlite3"))
        gate = ApprovalExecutionGate(db_path=str(root / "approval.sqlite3"))
        control = EnterpriseCommandControl(approval_gate=gate, db_path=str(root / "commands.sqlite3"))
        operational = FakeOperational()
        bridge = EventCommandBridge(events, control, operational, db_path=str(root / "bridge.sqlite3"))

        event = events.publish(
            "task.requested", "t1", "w1", "u1", "task", "x1", "x1",
            {"action": "create_task", "risk": "read"}
        )
        result = bridge.handle(event)
        assert result["command_status"] == "authorized"
        assert result["executed"] is True
        assert gate.history("t1", "w1")[0]["status"] == "approved"
