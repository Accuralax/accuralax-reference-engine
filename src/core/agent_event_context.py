from .event_bus import DomainEvent

class AgentEventContext:
    """Resolve durable business context before autonomous planning."""
    def __init__(self, workflow, lms=None):
        self.workflow = workflow
        self.lms = lms

    def resolve(self, event: DomainEvent):
        payload = dict(event.payload or {})
        lead = None
        opportunity = None
        learner = None
        client_id = payload.get("client_id")
        if event.event_type.startswith("sales.lead") and self.workflow.pipeline:
            lead = self.workflow.pipeline.get_lead(event.tenant_id, event.workspace_id, event.entity_id)
            client_id = client_id or (lead or {}).get("client_id")
        if event.event_type.startswith("sales.opportunity") and self.workflow.opportunities:
            opportunity = self.workflow.opportunities.get(event.tenant_id, event.workspace_id, event.entity_id)
            client_id = client_id or (opportunity or {}).get("client_id")
        if event.event_type.startswith("lms.") and self.lms and hasattr(self.lms, "get_learner"):
            learner = self.lms.get_learner(event.entity_id, event.tenant_id, event.workspace_id)
            client_id = client_id or (learner or {}).get("client_id")
        return {"client_id": client_id, "lead": lead, "opportunity": opportunity,
                "learner": learner, "event": payload}
