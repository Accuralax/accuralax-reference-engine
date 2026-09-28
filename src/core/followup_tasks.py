import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from .event_bus import EventBus

STATUSES = ("pending", "in_progress", "completed", "cancelled", "overdue")

class FollowUpTasks:
    """Tenant-scoped sales follow-up task queue with deterministic due-date handling and audit history."""

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join("data", "followup_tasks.sqlite3")
        self.events = EventBus(os.path.join(os.path.dirname(self.db_path) or ".", "event_bus.sqlite3"))
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS tasks(
                task_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, lead_id TEXT, opportunity_id TEXT, owner_id TEXT,
                title TEXT NOT NULL, channel TEXT, status TEXT NOT NULL, priority TEXT NOT NULL,
                due_at TEXT NOT NULL, completed_at TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS task_history(
                history_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                task_id TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL,
                changed_by TEXT NOT NULL, changed_at TEXT NOT NULL, reason TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(tenant_id,workspace_id,status,due_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(tenant_id,workspace_id,client_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_task_history ON task_history(tenant_id,workspace_id,task_id,changed_at)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def create(self, tenant_id, workspace_id, client_id, title, due_at=None, owner_id=None,
               lead_id=None, opportunity_id=None, channel="internal", priority="normal", notes=""):
        if not str(client_id).strip():
            raise ValueError("client_id_required")
        if not str(title).strip():
            raise ValueError("title_required")
        if due_at is None:
            due_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        due = self._parse(due_at)
        now = datetime.now(timezone.utc).isoformat()
        task_id = "TSK-" + uuid.uuid4().hex[:16].upper()
        with self._db() as c:
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (task_id, str(tenant_id), str(workspace_id), str(client_id),
                       lead_id, opportunity_id, owner_id, str(title), str(channel), "pending",
                       str(priority), due.isoformat(), None, str(notes), now, now))
            c.execute("INSERT INTO task_history VALUES(?,?,?,?,?,?,?,?,?)",
                      ("THS-" + uuid.uuid4().hex[:16].upper(), str(tenant_id), str(workspace_id),
                       task_id, None, "pending", "system", now, "task_created"))
        result = self.get(tenant_id, workspace_id, task_id)
        self.events.publish("sales.task.created", tenant_id, workspace_id, "system", "task", task_id, task_id, {"client_id": client_id, "lead_id": lead_id, "opportunity_id": opportunity_id, "due_at": due.isoformat()})
        return result

    @staticmethod
    def _parse(value):
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("invalid_due_at")
        if dt.tzinfo is None:
            raise ValueError("due_at_timezone_required")
        return dt.astimezone(timezone.utc)

    def get(self, tenant_id, workspace_id, task_id):
        with self._db() as c:
            row = c.execute("SELECT * FROM tasks WHERE tenant_id=? AND workspace_id=? AND task_id=?",
                            (str(tenant_id), str(workspace_id), str(task_id))).fetchone()
        return dict(row) if row else None

    def update_status(self, tenant_id, workspace_id, task_id, status, changed_by="system", reason=""):
        status = str(status)
        if status not in STATUSES:
            raise ValueError("invalid_status")
        task = self.get(tenant_id, workspace_id, task_id)
        if not task:
            raise ValueError("task_not_found")
        if task["status"] == status:
            return task
        now = datetime.now(timezone.utc).isoformat()
        completed = now if status == "completed" else task["completed_at"]
        with self._db() as c:
            c.execute("UPDATE tasks SET status=?, completed_at=?, updated_at=? WHERE tenant_id=? AND workspace_id=? AND task_id=?",
                      (status, completed, now, str(tenant_id), str(workspace_id), str(task_id)))
            c.execute("INSERT INTO task_history VALUES(?,?,?,?,?,?,?,?,?)",
                      ("THS-" + uuid.uuid4().hex[:16].upper(), str(tenant_id), str(workspace_id),
                       str(task_id), task["status"], status, str(changed_by), now, str(reason)))
        result = self.get(tenant_id, workspace_id, task_id)
        self.events.publish("sales.task.status_changed", tenant_id, workspace_id, str(changed_by), "task", task_id, task_id, {"from_status": task["status"], "to_status": status, "reason": reason})
        return result

    def due(self, tenant_id, workspace_id, as_of=None, owner_id=None):
        now = self._parse(as_of) if as_of else datetime.now(timezone.utc)
        args = [str(tenant_id), str(workspace_id), now.isoformat()]
        query = "SELECT * FROM tasks WHERE tenant_id=? AND workspace_id=? AND status IN ('pending','in_progress') AND due_at<=?"
        if owner_id:
            query += " AND owner_id=?"
            args.append(str(owner_id))
        query += " ORDER BY due_at"
        with self._db() as c:
            rows = c.execute(query, args).fetchall()
        return [dict(r) for r in rows]

    def mark_overdue(self, tenant_id, workspace_id, as_of=None):
        tasks = self.due(tenant_id, workspace_id, as_of)
        changed = []
        for task in tasks:
            changed.append(self.update_status(tenant_id, workspace_id, task["task_id"], "overdue", "system", "due_time_reached"))
        return changed

    def history(self, tenant_id, workspace_id, task_id):
        with self._db() as c:
            rows = c.execute("SELECT * FROM task_history WHERE tenant_id=? AND workspace_id=? AND task_id=? ORDER BY changed_at",
                             (str(tenant_id), str(workspace_id), str(task_id))).fetchall()
        return [dict(r) for r in rows]

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            history = c.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
        return {"status":"ok","engine":"followup-tasks","tenant_workspace_scoped":True,
                "due_date_normalization":"UTC","audit_history":True,
                "credentials_exposed":False,"tasks":count,"history":history}
