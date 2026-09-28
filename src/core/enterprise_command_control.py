from __future__ import annotations
import os
import sqlite3
import uuid
from datetime import datetime, timezone


class EnterpriseCommandControl:
    """Single governed runtime boundary for enterprise execution decisions."""

    def __init__(self, authorization=None, governance=None, approval_gate=None,
                 audit=None, observability=None, usage_billing=None,
                 recovery=None, orchestration=None, control_plane=None, db_path=None):
        self.authorization = authorization
        self.governance = governance
        self.approval_gate = approval_gate
        self.audit = audit
        self.observability = observability
        self.usage_billing = usage_billing
        self.recovery = recovery
        self.orchestration = orchestration
        self.control_plane = control_plane
        self.db_path = db_path or os.path.join("data", "enterprise_command_control.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS commands(
                command_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                actor_id TEXT NOT NULL, action TEXT NOT NULL, status TEXT NOT NULL,
                correlation_id TEXT NOT NULL, trace_id TEXT NOT NULL, result_json TEXT,
                reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_command_scope ON commands(tenant_id,workspace_id,created_at)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s, *a): c.commit(); c.close()
        return C()

    def _scope(self, tenant_id, workspace_id):
        if not tenant_id or not workspace_id:
            raise ValueError("tenant_id_and_workspace_id_required")
        return str(tenant_id), str(workspace_id)

    def authorize(self, tenant_id, workspace_id, actor_id, action, *,
                  role="MEMBER", risk="read", steps=0, cost=0,
                  tool=None, approved=False, high_risk=False,
                  destructive=False, external_side_effect=False):
        t, w = self._scope(tenant_id, workspace_id)
        reasons = []

        if self.authorization:
            decision = self.authorization.authorize(t, w, str(actor_id), str(action),
                                                     approved=approved)
            if not decision.get("allowed"):
                reasons.append(decision.get("reason", "authorization_denied"))

        if self.governance:
            decision = self.governance.check(
                t, w, str(actor_id), str(action), risk=risk, steps=steps,
                cost=cost, tool=tool, approved=approved)
            if not decision.get("allowed"):
                reasons.extend(decision.get("reasons", [decision.get("reason", "governance_denied")]))

        if self.control_plane:
            decision = self.control_plane.authorize(
                str(action), high_risk=high_risk or risk in ("external", "destructive"),
                destructive=destructive or risk == "destructive",
                external_side_effect=external_side_effect or risk == "external",
                approved=approved)
            if not decision.get("allowed"):
                reasons.extend(decision.get("reasons", []))

        approval_required = bool((high_risk or risk in ("high", "critical", "external", "destructive") or destructive or external_side_effect) and not approved)
        return {
            "allowed": not reasons and not approval_required,
            "tenant_id": t,
            "workspace_id": w,
            "actor_id": str(actor_id),
            "action": str(action),
            "role": str(role),
            "risk": str(risk),
            "approval_required": approval_required,
            "reasons": list(dict.fromkeys(reasons + (["approval_required"] if approval_required else []))),
        }

    def request(self, tenant_id, workspace_id, actor_id, action, *,
                risk="read", steps=0, cost=0, tool=None,
                high_risk=False, destructive=False, external_side_effect=False,
                correlation_id=None, trace_id=None):
        t, w = self._scope(tenant_id, workspace_id)
        command_id = "CMD-" + uuid.uuid4().hex[:16].upper()
        correlation_id = correlation_id or "CORR-" + uuid.uuid4().hex[:12].upper()
        trace_id = trace_id or "TRACE-" + uuid.uuid4().hex[:12].upper()
        decision = self.authorize(
            t, w, actor_id, action, risk=risk, steps=steps, cost=cost,
            tool=tool, approved=False, high_risk=high_risk,
            destructive=destructive, external_side_effect=external_side_effect)
        status = "awaiting_approval" if decision["approval_required"] else "authorized"
        now = datetime.now(timezone.utc).isoformat()
        approval = None
        if self.approval_gate:
            approval = self.approval_gate.request(
                t, w, command_id, str(action), risk=risk, actor_id=str(actor_id),
                requires_approval=decision["approval_required"], trace_id=trace_id,
                correlation_id=correlation_id)
            if approval.get("status") == "pending_approval":
                status = "awaiting_approval"
        with self._db() as c:
            c.execute("INSERT INTO commands VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (command_id, t, w, str(actor_id), str(action), status,
                       correlation_id, trace_id, None,
                       ";".join(decision["reasons"]), now, now))
        self._record("command.requested", t, w, str(actor_id), command_id, status, correlation_id, trace_id)
        return {"command_id": command_id, "status": status, "correlation_id": correlation_id,
                "trace_id": trace_id, "decision": decision, "approval": approval}

    def _record(self, event_type, tenant_id, workspace_id, actor_id, command_id, status, correlation_id, trace_id):
        if self.audit:
            try:
                self.audit.record(tenant_id, workspace_id, actor_id, event_type, source="command", status=status, entity_type="command", entity_id=command_id, reference_id=command_id, trace_id=trace_id, correlation_id=correlation_id,
                                  metadata={"correlation_id": correlation_id, "trace_id": trace_id})
            except Exception:
                pass
        if self.observability:
            try:
                self.observability.log(tenant_id, workspace_id, "info", event_type, trace_id=trace_id,
                                       correlation_id=correlation_id,
                                       metadata={"command_id": command_id, "status": status})
            except Exception:
                pass

    def approve(self, tenant_id, workspace_id, command_id, approved_by, approved=True, reason=""):
        t, w = self._scope(tenant_id, workspace_id)
        with self._db() as c:
            row = c.execute("SELECT * FROM commands WHERE command_id=? AND tenant_id=? AND workspace_id=?",
                            (str(command_id), t, w)).fetchone()
        if not row:
            raise KeyError("command_not_found")
        if not self.approval_gate:
            raise RuntimeError("approval_gate_not_connected")
        pending = self.approval_gate.history(t, w, limit=500)
        decision = next((x for x in pending if x["run_id"] == str(command_id)), None)
        if not decision:
            raise KeyError("approval_decision_not_found")
        result = self.approval_gate.approve(t, w, decision["decision_id"], str(approved_by), approved, reason,
                                             trace_id=row["trace_id"], correlation_id=row["correlation_id"])
        status = "authorized" if approved else "rejected"
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE commands SET status=?,reason=?,updated_at=? WHERE command_id=? AND tenant_id=? AND workspace_id=?",
                      (status, reason or status, now, str(command_id), t, w))
        self._record("command.approval", t, w, str(approved_by), str(command_id), status,
                     row["correlation_id"], row["trace_id"])
        return {"command_id": str(command_id), "status": status, "approved": bool(approved), "approval": result}

    def get(self, tenant_id, workspace_id, command_id):
        t, w = self._scope(tenant_id, workspace_id)
        with self._db() as c:
            row = c.execute("SELECT * FROM commands WHERE command_id=? AND tenant_id=? AND workspace_id=?",
                            (str(command_id), t, w)).fetchone()
        if not row:
            raise KeyError("command_not_found")
        return dict(row)

    def health(self):
        with self._db() as c:
            total = c.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
            pending = c.execute("SELECT COUNT(*) FROM commands WHERE status='awaiting_approval'").fetchone()[0]
        return {
            "status": "ok",
            "engine": "enterprise-command-control",
            "durable": True,
            "tenant_workspace_scoped": True,
            "centralized_authorization": self.authorization is not None,
            "centralized_governance": self.governance is not None,
            "approval_boundary": self.approval_gate is not None,
            "audit_connected": self.audit is not None,
            "observability_connected": self.observability is not None,
            "usage_connected": self.usage_billing is not None,
            "recovery_connected": self.recovery is not None,
            "orchestration_connected": self.orchestration is not None,
            "capability_policy_connected": self.control_plane is not None,
            "commands": total,
            "pending_approval": pending,
        }
