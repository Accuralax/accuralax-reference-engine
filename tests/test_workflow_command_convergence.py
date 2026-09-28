from pathlib import Path

from src.core.enterprise_command_control import EnterpriseCommandControl
from src.core.operational_execution import OperationalExecution
from src.core.task_assignment import TaskAssignment
from src.core.workflow_automation import WorkflowAutomation


def test_workflow_execution_uses_command_control(tmp_path: Path):
    workflows = WorkflowAutomation(str(tmp_path / "workflow.sqlite3"))
    control = EnterpriseCommandControl(db_path=str(tmp_path / "commands.sqlite3"))
    wf = workflows.define("t1", "w1", "Governed task", "task.requested", [
        {"action": "create_task", "data": {"title": "Governed work"}}
    ])
    run = workflows.start("t1", "w1", wf["workflow_id"], {})
    result = workflows.execute(
        "t1", "w1", run["run_id"],
        executor=lambda step: {"ok": True},
        command_control=control, actor_id="u1", risk="read",
    )
    assert result["status"] == "completed"


def test_high_risk_workflow_is_blocked_without_approval(tmp_path: Path):
    workflows = WorkflowAutomation(str(tmp_path / "workflow.sqlite3"))
    control = EnterpriseCommandControl(db_path=str(tmp_path / "commands.sqlite3"))
    wf = workflows.define("t1", "w1", "Sensitive workflow", "security.action.requested", [
        {"action": "notify", "requires_approval": True}
    ])
    run = workflows.start("t1", "w1", wf["workflow_id"], {})
    result = workflows.execute(
        "t1", "w1", run["run_id"],
        command_control=control, actor_id="u1", risk="high", approved=False,
    )
    assert result["status"] == "blocked"
    assert result["result"]["reason"] == "command_control_denied"
