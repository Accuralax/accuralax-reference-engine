from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class ITTicket:
    ticket_id: str
    reference_id: str
    request: str
    ticket_type: str
    priority: str
    status: str = "open"
    assigned_agent: str | None = None
    sla_target_minutes: int = 480
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified: bool = False


class ITServiceManager:
    """Local ITSM state model; external ticket systems remain behind approved gateways."""

    SLA = {"critical": 60, "high": 240, "medium": 480, "low": 1440}

    def create_ticket(self, reference_id: str, request: str, *, ticket_type: str = "incident", priority: str = "medium", assigned_agent: str | None = None) -> ITTicket:
        if priority not in self.SLA:
            priority = "medium"
        return ITTicket(
            ticket_id=f"IT-{uuid.uuid4().hex[:10].upper()}",
            reference_id=reference_id,
            request=request.strip(),
            ticket_type=ticket_type,
            priority=priority,
            assigned_agent=assigned_agent,
            sla_target_minutes=self.SLA[priority],
        )

    @staticmethod
    def classify_ticket_type(request: str) -> str:
        text = request.lower()
        if any(x in text for x in ("not working", "error", "down", "failed", "incident")):
            return "incident"
        if any(x in text for x in ("install", "setup", "configure", "request", "need")):
            return "service_request"
        return "incident"

    @staticmethod
    def infer_priority(request: str) -> str:
        text = request.lower()
        if any(x in text for x in ("critical", "outage", "all users", "production down")):
            return "critical"
        if any(x in text for x in ("urgent", "security incident", "business stopped")):
            return "high"
        if any(x in text for x in ("minor", "when possible", "low priority")):
            return "low"
        return "medium"

    def close_after_verification(self, ticket: ITTicket, *, verified: bool) -> ITTicket:
        ticket.verified = verified
        ticket.status = "resolved" if verified else "open"
        return ticket

    @staticmethod
    def snapshot() -> dict[str, Any]:
        return {"sla_priorities": list(ITServiceManager.SLA), "external_execution": "gateway_only", "verification_before_resolution": True, "credentials_exposed_to_agents": False}
