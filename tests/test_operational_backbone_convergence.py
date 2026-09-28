import tempfile
from pathlib import Path

from src.core.audit_lineage import AuditLineage
from src.core.case_management import CaseManagement
from src.core.notifications import NotificationCenter
from src.core.observability import Observability
from src.core.operational_execution import OperationalExecution
from src.core.sla_escalation import SLAEscalation
from src.core.task_assignment import TaskAssignment


def build(root: Path):
    tasks = TaskAssignment(db_path=str(root / "tasks.sqlite3"))
    cases = CaseManagement(db_path=str(root / "cases.sqlite3"))
    sla = SLAEscalation(db_path=str(root / "sla.sqlite3"))
    notifications = NotificationCenter(db_path=str(root / "notifications.sqlite3"))
    audit = AuditLineage(db_path=str(root / "audit.sqlite3"))
    observability = Observability(db_path=str(root / "observability.sqlite3"))
    op = OperationalExecution(
        tasks,
        sla=sla,
        cases=cases,
        notifications=notifications,
        audit=audit,
        observability=observability,
        db_path=str(root / "ops.sqlite3"),
    )
    return op, tasks, cases, sla, notifications, audit, observability


def test_event_converges_task_case_sla_notification_and_telemetry():
    with tempfile.TemporaryDirectory() as d:
        op, tasks, cases, sla, notifications, audit, observability = build(Path(d))
        case = cases.create_case("t1", "w1", "Customer escalation", created_by="u1")
        policy = sla.define_policy("t1", "w1", "Fast response", "task", 1)
        result = op.execute_event(
            "t1", "w1", "evt-1", "case.created",
            {
                "case_id": case["case_id"],
                "sla_policy_id": policy["policy_id"],
                "notification": {
                    "recipient_id": "u1",
                    "channel": "in_app",
                    "subject": "Case created",
                    "body": "A case needs attention",
                },
            },
            "u1",
        )
        assert result["status"] == "awaiting_execution"
        assert result["result"]["task_created"] is True
        assert result["result"]["sla_started"] is True
        assert result["result"]["notification_queued"] is True
        task = tasks.get("t1", "w1", result["result"]["task_id"])
        assert task["reference_id"] == "evt-1"
        sla_history = sla.history("t1", "w1")
        assert sla_history and sla_history[0]["event_type"] == "started"
        sla_item = sla.get("t1", "w1", sla_history[0]["item_id"])
        assert sla_item["reference_type"] == "task"
        assert sla_item["reference_id"] == task["task_id"]
        assert notifications.history("t1", "w1")[0]["state"] == "queued"
        assert audit.history("t1", "w1")[0]["event_type"] == "operational.execution"
        assert observability.snapshot("t1", "w1")["logs"]

def test_event_execution_is_idempotent_and_traces_completion():
    with tempfile.TemporaryDirectory() as d:
        op, tasks, _cases, _sla, _notifications, audit, observability = build(Path(d))
        first = op.execute_event(
            "t1", "w1", "evt-2", "task.requested",
            {"task_title": "Do work", "priority": "high"},
            "u1", auto_execute=True, trace_id="trace-2", correlation_id="corr-2",
        )
        second = op.execute_event(
            "t1", "w1", "evt-2", "task.requested",
            {"task_title": "Do work", "priority": "high"},
            "u1", auto_execute=True, trace_id="trace-2", correlation_id="corr-2",
        )
        assert first["status"] == "completed"
        assert second["status"] == "already_processed"
        assert len(tasks.list("t1", "w1")) == 1
        audit_item = audit.history("t1", "w1")[0]
        assert audit_item["trace_id"] == "trace-2"
        assert audit_item["correlation_id"] == "corr-2"
        assert audit_item["entity_id"] == first["run_id"]
        snapshot = observability.snapshot("t1", "w1")
        assert snapshot["logs"][0]["trace_id"] == "trace-2"
