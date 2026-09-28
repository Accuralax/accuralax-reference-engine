from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from contextlib import contextmanager

class OperationalExecution:
    """Governed bridge for end-to-end operational execution across workflow, task, case, SLA and notification layers."""

    def _workflow_step_executor(self, tenant_id, workspace_id, actor_id, event_id, step, payload):
        action = str(step.get("action", "")).lower()
        data = dict(step.get("data") or {})
        context = dict(payload.get("workflow_input") or {})
        context.update(data)
        if action in {"create_task", "task.create"}:
            task = self.tasks.create(
                tenant_id, workspace_id, context.get("title") or context.get("task_title") or "Workflow task",
                actor_id, description=context.get("description", ""), priority=context.get("priority", "normal"),
                assignee_id=context.get("assignee_id"), reference_type="workflow", reference_id=event_id,
                metadata={"workflow_step": True, "source_event": event_id})
            return {"task_id": task["task_id"], "status": "created"}
        if action in {"start_sla", "sla.start"} and self.sla:
            item_id = context.get("item_id") or context.get("task_id")
            result = self.sla.start(tenant_id, workspace_id, context["sla_policy_id"], item_id, actor_id)
            return {"sla": result, "status": "started"}
        if action in {"notify", "notification.send"} and self.notifications:
            notice = context.get("notification") or context
            result = self.notifications.queue(
                tenant_id, workspace_id, notice.get("recipient_id", actor_id), notice.get("channel", "in_app"),
                notice.get("subject", ""), notice.get("body", ""), notice.get("template_id"), event_id,
                notice.get("data", {}))
            return {"notification": result, "status": "queued"}
        if action in {"case.add_task", "case_link_task"} and self.cases:
            result = self.cases.add_task(tenant_id, workspace_id, context["case_id"],
                                         context.get("title") or context.get("task_title") or "Workflow task",
                                         context.get("assignee_id", actor_id), context.get("due_at"))
            return {"case_task": result, "status": "linked"}
        if action in {"event.dispatch", "event.route"} and self.event_automation:
            return self.event_automation.dispatch(tenant_id, workspace_id, event_id,
                                                  context.get("event_type", "workflow.step"), context)
        raise ValueError(f"unsupported_workflow_action:{action}")
    def __init__(self, tasks, workflows=None, sla=None, cases=None, notifications=None, event_automation=None, db_path=None, command_control=None, audit=None, observability=None):
        self.tasks=tasks; self.workflows=workflows; self.sla=sla; self.cases=cases
        self.notifications=notifications; self.event_automation=event_automation; self.command_control=command_control
        self.audit=audit or getattr(command_control, "audit", None)
        self.observability=observability or getattr(command_control, "observability", None)
        self.db_path=db_path or os.path.join("data","operational_execution.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,event_id TEXT,event_type TEXT,status TEXT,task_id TEXT,result TEXT,created_at TEXT,updated_at TEXT,trace_id TEXT,correlation_id TEXT,UNIQUE(tenant_id,workspace_id,event_id))")
    @contextmanager
    def db(self):
        c = sqlite3.connect(self.db_path, timeout=15.0)
        c.execute("PRAGMA busy_timeout=15000")
        try:
            yield c
            c.commit()
        finally:
            c.close()
    def now(self): return datetime.now(timezone.utc).isoformat()
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def _telemetry(self,t,w,actor,event_type,status,run_id=None,task_id=None,trace_id=None,correlation_id=None,metadata=None):
        if self.audit:
            try:self.audit.record(t,w,actor,event_type,source="operational_execution",status=status,entity_type="operational_run",entity_id=run_id,reference_id=task_id,trace_id=trace_id,correlation_id=correlation_id,metadata=metadata or {})
            except Exception:pass
        if self.observability:
            try:self.observability.log(t,w,"INFO",event_type,trace_id=trace_id,correlation_id=correlation_id,metadata=dict(metadata or {},run_id=run_id,task_id=task_id,status=status))
            except Exception:pass

    def execute_event(self,t,w,event_id,event_type,payload,actor_id="system",auto_execute=False,trace_id=None,correlation_id=None):
        t,w=self.scope(t,w)
        with self.db() as c:
            old=c.execute("SELECT run_id,status,task_id,result FROM runs WHERE tenant_id=? AND workspace_id=? AND event_id=?",(t,w,event_id)).fetchone()
        if old:return {"status":"already_processed","run_id":old[0],"task_id":old[2],"result":json.loads(old[3] or "{}")}
        if auto_execute and self.command_control:
            decision = self.command_control.authorize(t, w, actor_id, "execute", risk=str(payload.get("risk", "read")), approved=bool(payload.get("approved", False)))
            if not decision["allowed"]:
                self._telemetry(t,w,actor_id,"operational.execution_denied","blocked",trace_id=trace_id,correlation_id=correlation_id,metadata={"event_id":event_id,"event_type":event_type,"reason":"command_control_denied"})
                return {"status":"blocked","reason":"command_control_denied","decision":decision}
        title=payload.get("task_title") or f"{event_type} work item"
        priority=payload.get("priority","normal")
        task=self.tasks.create(t,w,title,actor_id,description=payload.get("description",""),priority=priority,assignee_id=payload.get("assignee_id"),reference_type=payload.get("reference_type") or event_type,reference_id=payload.get("reference_id") or event_id,metadata={"source_event":event_id,"event_type":event_type})
        run_id="RUN-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        result={"task_created":True,"task_id":task["task_id"],"sla_started":False,"notification_queued":False}
        if self.sla and payload.get("sla_policy_id"):
            try:
                self.sla.start(t,w,payload["sla_policy_id"],task["task_id"],actor_id)
                result["sla_started"]=True
            except Exception as exc: result["sla_error"]=str(exc)
        if self.notifications and payload.get("notification"):
            try:
                notice = payload["notification"]
                self.notifications.queue(t, w, notice.get("recipient_id", actor_id), notice.get("channel", "in_app"), notice.get("subject", ""), notice.get("body", ""), notice.get("template_id"), event_id, notice.get("data", {}))
                result["notification_queued"]=True
            except Exception as exc:
                result["notification_error"]=str(exc)
        if self.cases and payload.get("case_id"):
            try:
                self.cases.add_task(t, w, payload["case_id"], title, payload.get("assignee_id", actor_id), payload.get("due_at"))
                result["case_linked"]=True
            except Exception as exc:
                result["case_error"]=str(exc)
        if self.workflows and payload.get("workflow_id") and auto_execute:
            try:
                wf = self.workflows.start(t, w, payload["workflow_id"], payload.get("workflow_input", {}))
                result["workflow_started"] = True
                result["workflow"] = wf
                if wf.get("run_id"):
                    workflow_result = self.workflows.execute(
                        t, w, wf["run_id"],
                        executor=lambda step: self._workflow_step_executor(t, w, actor_id, event_id, step, payload),
                        approved=bool(payload.get("approved", False)),
                    )
                    result["workflow"] = workflow_result
                    result["workflow_executed"] = workflow_result.get("status") == "completed"
            except Exception as exc:
                result["workflow_error"]=str(exc)
        if self.event_automation and auto_execute:
            try:
                routed = self.event_automation.dispatch(t, w, event_id, event_type, payload)
                result["event_automation"] = routed
            except Exception as exc:
                result["event_automation_error"] = str(exc)
        errors=[k for k in result if k.endswith("_error")]
        status=("failed" if errors else "completed") if auto_execute else "awaiting_execution"
        if errors: result["execution_errors"]=errors
        if self.command_control and auto_execute:
            try:
                if self.command_control.audit:
                    self.command_control.audit.record(t,w,actor_id,"operational.execution","operational_execution",status, "task",task["task_id"],event_id, None, None, result)
                if self.command_control.observability:
                    self.command_control.observability.log(t,w,"INFO","operational execution completed",metadata=result)
            except Exception as exc:
                result["telemetry_error"]=str(exc)
        with self.db() as c:c.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(run_id,t,w,event_id,event_type,status,task["task_id"],json.dumps(result),now,now,trace_id,correlation_id))
        return {"status":status,"run_id":run_id,"task":task,"result":result}
    def history(self,t,w,limit=100):
        t,w=self.scope(t,w)
        with self.db() as c:rows=c.execute("SELECT run_id,event_id,event_type,status,task_id,result,created_at,updated_at,trace_id,correlation_id FROM runs WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",(t,w,int(limit))).fetchall()
        out=[]
        for r in rows:
            d=dict(zip(("run_id","event_id","event_type","status","task_id","result","created_at","updated_at","trace_id","correlation_id"),r)); d["result"]=json.loads(d["result"] or "{}"); out.append(d)
        return out
    def health(self):
        with self.db() as c:n=c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        return {"status":"ok","runs":n,"tenant_scoped":True,"approval_aware":True,"idempotent_events":True}
