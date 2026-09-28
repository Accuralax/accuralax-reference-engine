from src.core.followup_tasks import FollowUpTasks

def test_followup_task_lifecycle_and_due(tmp_path):
    e = FollowUpTasks(str(tmp_path / "tasks.sqlite3"))
    task = e.create("t1", "w1", "CLI-1", "Call client", "2026-10-01T09:00:00+02:00", "owner-1", "LED-1", "OPP-1", "phone", "high")
    assert task["due_at"] == "2026-10-01T07:00:00+00:00"
    due = e.due("t1", "w1", "2026-10-01T08:00:00+00:00")
    assert len(due) == 1
    completed = e.update_status("t1", "w1", task["task_id"], "completed", "owner-1", "call_done")
    assert completed["completed_at"] is not None
    assert len(e.history("t1", "w1", task["task_id"])) == 2

def test_followup_validation_and_scope(tmp_path):
    e = FollowUpTasks(str(tmp_path / "tasks.sqlite3"))
    try:
        e.create("t1", "w1", "CLI-1", "Call", "2026-10-01T09:00:00")
        assert False
    except ValueError as exc:
        assert str(exc) == "due_at_timezone_required"
    task = e.create("t1", "w1", "CLI-1", "Call")
    assert e.get("t2", "w1", task["task_id"]) is None
    try:
        e.update_status("t1", "w1", task["task_id"], "bad")
        assert False
    except ValueError as exc:
        assert str(exc) == "invalid_status"
