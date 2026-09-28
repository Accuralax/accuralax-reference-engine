from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone


class EventCommandBridge:
    """Routes durable domain events through the same governed command boundary."""
    RISK_BY_EVENT = {
        "security.action.requested": "high",
        "compliance.action.requested": "high",
        "data.deletion.requested": "destructive",
        "external.action.requested": "external",
    }

    def __init__(self, event_bus, command_control, operational_execution=None, db_path=None):
        self.events = event_bus
        self.control = command_control
        self.operational = operational_execution
        self.db_path = db_path or os.path.join("data", "event_command_bridge.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS dispatches(
                event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                command_id TEXT, status TEXT NOT NULL, result_json TEXT,
                trace_id TEXT, correlation_id TEXT, created_at TEXT NOT NULL)""")
            cols={r[1] for r in c.execute("PRAGMA table_info(dispatches)").fetchall()}
            for col in ("trace_id", "correlation_id"):
                if col not in cols: c.execute(f"ALTER TABLE dispatches ADD COLUMN {col} TEXT")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s, *a): c.commit(); c.close()
        return C()

    def subscribe(self, event_types=None):
        for event_type in event_types or ["*"]:
            if event_type == "*":
                continue
            self.events.subscribe(event_type, self.handle)
        return {"subscribed": list(event_types or [])}

    def handle(self, event):
        with self._db() as c:
            old = c.execute("SELECT * FROM dispatches WHERE event_id=?", (event.event_id,)).fetchone()
        if old:
            return self._row(old)

        payload = dict(event.payload or {})
        risk = str(payload.get("risk") or self.RISK_BY_EVENT.get(event.event_type, "read")).lower()
        action = str(payload.get("action") or "execute")
        request = self.control.request(
            event.tenant_id, event.workspace_id, event.actor_id, action,
            risk=risk, steps=int(payload.get("steps", 0)),
            cost=float(payload.get("cost", 0)), tool=payload.get("tool"),
            high_risk=risk in ("high", "critical"),
            destructive=risk == "destructive",
            external_side_effect=risk == "external",
            correlation_id=payload.get("correlation_id"),
            trace_id=event.trace_id,
        )
        status = request["status"]
        result = {"event_id": event.event_id, "command_id": request["command_id"],
                  "command_status": status, "executed": False}

        if status == "authorized" and self.operational:
            op = self.operational.execute_event(
                event.tenant_id, event.workspace_id, event.event_id,
                event.event_type, payload, event.actor_id,
                auto_execute=(status == "authorized"), trace_id=event.trace_id,
                correlation_id=request.get("correlation_id") or payload.get("correlation_id"))
            result["operational"] = op
            result["executed"] = op.get("status") == "completed"
            if op.get("status") != "completed":
                status = "failed"

        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("INSERT INTO dispatches(event_id,tenant_id,workspace_id,command_id,status,result_json,trace_id,correlation_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                      (event.event_id, event.tenant_id, event.workspace_id, request["command_id"], status, json.dumps(result, sort_keys=True), request.get("trace_id"), request.get("correlation_id"), now))
        return result

    def approve_and_resume(self, tenant_id, workspace_id, command_id, approved_by, approved=True, reason=""):
        command = self.control.get(tenant_id, workspace_id, command_id)
        approval = self.control.approve(tenant_id, workspace_id, command_id, approved_by, approved, reason)
        if not approved:
            return {"command_id": command_id, "status": "rejected", "approval": approval, "executed": False}
        if not self.operational:
            return {"command_id": command_id, "status": "authorized", "approval": approval, "executed": False,
                    "reason": "operational_execution_not_connected"}
        events = self.events.history(tenant_id, workspace_id, limit=500)
        event = next((e for e in events if e.event_id == command.get("result_event_id") or
                      e.event_id == next((d["event_id"] for d in self.history(tenant_id, workspace_id, 500)
                                          if d.get("command_id") == command_id), "")), None)
        if not event:
            # Fall back to the command correlation and persisted dispatch result to locate the source event.
            rows = self.history(tenant_id, workspace_id, 500)
            dispatch = next((d for d in rows if d.get("command_id") == command_id), None)
            if dispatch:
                event = next((e for e in events if e.event_id == dispatch.get("event_id")), None)
        if not event:
            return {"command_id": command_id, "status": "authorized", "approval": approval, "executed": False,
                    "reason": "source_event_not_found"}
        op = self.operational.execute_event(
            event.tenant_id, event.workspace_id, event.event_id, event.event_type,
            dict(event.payload or {}), event.actor_id, auto_execute=True,
            trace_id=command.get("trace_id"), correlation_id=command.get("correlation_id"))
        status = "completed" if op.get("status") == "completed" else "failed"
        with self._db() as c:
            c.execute("UPDATE dispatches SET status=?,result_json=? WHERE event_id=? AND tenant_id=? AND workspace_id=?",
                      (status, json.dumps({"event_id": event.event_id, "command_id": command_id,
                                           "command_status": "authorized", "executed": status == "completed",
                                           "operational": op}, sort_keys=True), event.event_id,
                       str(tenant_id), str(workspace_id)))
        return {"command_id": command_id, "status": status, "approval": approval,
                "executed": status == "completed", "operational": op}

    @staticmethod
    def _row(row):
        d = dict(row)
        d["result_json"] = json.loads(d["result_json"] or "{}")
        return d

    def history(self, tenant_id, workspace_id, limit=100):
        with self._db() as c:
            rows = c.execute(
                "SELECT * FROM dispatches WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",
                (str(tenant_id), str(workspace_id), max(1, min(int(limit), 500)))
            ).fetchall()
        return [self._row(r) for r in rows]

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM dispatches").fetchone()[0]
        return {"status": "ok", "durable": True, "event_count": count,
                "tenant_workspace_scoped": True, "governed": True,
                "approval_aware": True, "idempotent": True}
