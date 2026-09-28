from __future__ import annotations

from datetime import datetime, timezone


class EnterpriseControlCenter:
    """Read-oriented enterprise operating view over governed runtime subsystems."""

    def __init__(self, command_control=None, agent_registry=None, evaluation=None,
                 model_gateway=None, observability=None, usage_billing=None, audit=None):
        self.command_control=command_control
        self.agent_registry=agent_registry
        self.evaluation=evaluation
        self.model_gateway=model_gateway
        self.observability=observability
        self.usage_billing=usage_billing
        self.audit=audit

    def snapshot(self, tenant_id, workspace_id):
        t,w=str(tenant_id),str(workspace_id)
        agents=self.agent_registry.list_agents(t,w) if self.agent_registry else []
        skills=self.agent_registry.list_skills(t,w) if self.agent_registry else []
        latest=[]
        if self.evaluation:
            for a in agents:
                item=self.evaluation.latest(t,w,a.get("agent_id"))
                if item: latest.append(item)
        usage=self.usage_billing.invoice_preview(t,w) if self.usage_billing else None
        audit=self.audit.history(t,w,limit=25) if self.audit else []
        security_events=[x for x in audit if str(x.get("event_type","")).startswith("authorization.")]
        return {
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "tenant_id":t,"workspace_id":w,
            "runtime":self.command_control.health() if self.command_control else None,
            "agents":{"total":len(agents),"active":sum(a.get("status")=="active" for a in agents),"items":agents},
            "skills":{"total":len(skills),"active":sum(s.get("status")=="active" for s in skills),"items":skills},
            "evaluation":{"latest":latest,"count":len(latest),"healthy":all(x.get("passed") for x in latest) if latest else True},
            "model_gateway":self.model_gateway.health() if self.model_gateway else None,
            "observability":self.observability.health() if self.observability else None,
            "usage":usage,
            "security":{"authorization_events":len(security_events),"recent":security_events},
        }

    def health(self):
        return {"status":"ok","tenant_scoped":True,"read_only_snapshot":True,
                "command_control_connected":self.command_control is not None,
                "agent_registry_connected":self.agent_registry is not None,
                "evaluation_connected":self.evaluation is not None,
                "model_gateway_connected":self.model_gateway is not None,
                "observability_connected":self.observability is not None,
                "usage_connected":self.usage_billing is not None}
