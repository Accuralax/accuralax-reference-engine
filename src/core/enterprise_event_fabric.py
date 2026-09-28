from __future__ import annotations
import uuid
from .enterprise_entity_model import EnterpriseEntityModel
from .event_bus import EventBus

class EnterpriseEventFabric:
    """Governed bridge between enterprise entities and durable domain events."""
    def __init__(self, entity_model=None, event_bus=None):
        self.entities = entity_model or EnterpriseEntityModel()
        self.events = event_bus or EventBus()

    @staticmethod
    def _scope(tenant_id, workspace_id):
        if not tenant_id or not workspace_id:
            raise ValueError("tenant_id_and_workspace_id_required")
        return str(tenant_id), str(workspace_id)

    def publish_entity_event(self, tenant_id, workspace_id, actor_id, entity_type, payload,
                             event_type, reference_id="", idempotency_key=None, trace_id=None):
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        entity = self.entities.upsert(tenant_id, workspace_id, entity_type, payload)
        event = self.events.publish(
            event_type, tenant_id, workspace_id, str(actor_id or "system"),
            entity_type, entity["entity_id"], reference_id or entity["entity_id"],
            payload, idempotency_key=idempotency_key or f"{event_type}:{entity['entity_id']}:{entity['status']}",
            trace_id=trace_id or "TRACE-" + uuid.uuid4().hex[:12].upper(),
        )
        return {"status": entity["status"], "entity": entity, "event": event}

    def publish_relationship_event(self, tenant_id, workspace_id, actor_id, source_id, target_id,
                                   relationship_type, event_type="relationship.created",
                                   idempotency_key=None, trace_id=None):
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        relationship = self.entities.link(tenant_id, workspace_id, source_id, target_id, relationship_type)
        event = self.events.publish(
            event_type, tenant_id, workspace_id, str(actor_id or "system"),
            "relationship", relationship["relationship_id"], relationship["relationship_id"],
            relationship, idempotency_key=idempotency_key or f"{event_type}:{relationship['relationship_id']}",
            trace_id=trace_id or "TRACE-" + uuid.uuid4().hex[:12].upper(),
        )
        return {"status": relationship["status"], "relationship": relationship, "event": event}

    def history(self, tenant_id, workspace_id, **kwargs):
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        return self.events.history(tenant_id, workspace_id, **kwargs)

    def health(self):
        return {"status":"ok","engine":"enterprise-event-fabric","entity_event_bridge":True,
                "relationship_events":True,"tenant_isolation":True,"workspace_isolation":True,
                "idempotency":True,"trace_ids":True}
