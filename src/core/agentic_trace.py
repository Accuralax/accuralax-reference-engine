from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class TraceEvent:
    event_id: str
    reference_id: str
    node: str
    status: str
    details: dict[str, Any]
    created_at: str


@dataclass
class AgenticTrace:
    reference_id: str
    events: list[TraceEvent] = field(default_factory=list)

    def record(self, node: str, status: str, **details: Any) -> TraceEvent:
        safe = self._safe(details)
        event = TraceEvent(
            event_id=f"TRC-{uuid.uuid4().hex[:12].upper()}",
            reference_id=self.reference_id,
            node=node,
            status=status,
            details=safe,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.events.append(event)
        return event

    def summary(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "event_count": len(self.events),
            "nodes": [event.node for event in self.events],
            "statuses": [event.status for event in self.events],
            "credentials_exposed": False,
        }

    @classmethod
    def _safe(cls, value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): cls._safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [cls._safe(v) for v in value]
        return value
