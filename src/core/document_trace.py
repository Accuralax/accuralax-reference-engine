from __future__ import annotations
from .agentic_trace import AgenticTrace

class DocumentTrace:
    """Trace adapter for document workflows; never stores credentials."""
    def __init__(self, reference_id: str):
        self.trace = AgenticTrace(reference_id)

    def stage(self, node: str, status: str, **details):
        self.trace.record(node, status, **details)

    def summary(self) -> dict:
        return self.trace.summary()

    def events(self) -> list[dict]:
        return [
            {
                "event_id": event.event_id,
                "reference_id": event.reference_id,
                "node": event.node,
                "status": event.status,
                "details": event.details,
                "created_at": event.created_at,
            }
            for event in self.trace.events
        ]
