import tempfile
from pathlib import Path
from src.core.task_assignment import TaskAssignment
from src.core.workflow_automation import WorkflowAutomation
from src.core.operational_execution import OperationalExecution


def test_operational_execution_runs_workflow_steps_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        tasks = TaskAssignment(db_path=str(root / "tasks.sqlite3"))
        workflows = WorkflowAutomation(db_path=str(root / "workflows.sqlite3"))
        op = OperationalExecution(tasks, workflows=workflows, db_path=str(root / "ops.sqlite3"))
        wf = workflows.define("t1", "w1", "Task flow", "task.requested", [
            {"action": "create_task", "data": {"title": "Follow-up work", "priority": "high"}},
        ])
        result = op.execute_event("t1", "w1", "evt-1", "task.requested", {
            "workflow_id": wf["workflow_id"], "workflow_input": {}, "approved": True
        }, "u1", auto_execute=True)
        assert result["status"] == "completed"
        assert result["result"]["workflow_executed"] is True
        assert result["result"]["workflow"]["status"] == "completed"
        assert len(result["result"]["workflow"]["result"]["steps"]) == 1
