from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .it_asset_management import ITAssetManager
from .it_service_management import ITServiceManager, ITTicket
from .it_sla import ITSLAManager, SLACase
from .it_support_team import ITSupportTeam, classify_it_request, contains_secret_request


@dataclass
class ITWorkOrder:
    ticket: ITTicket
    sla: SLACase
    asset_ids: list[str] = field(default_factory=list)
    workstream: str | None = None
    assigned_agent: str | None = None
    status: str = "triaged"
    approval_required: bool = False
    verification_required: bool = True
    audit: list[dict[str, Any]] = field(default_factory=list)


class ITIncidentOrchestrator:
    """Unify ticket, CMDB, SLA, specialist routing, approval and verification gates."""

    def __init__(
        self,
        *,
        team: ITSupportTeam | None = None,
        service_manager: ITServiceManager | None = None,
        asset_manager: ITAssetManager | None = None,
        sla_manager: ITSLAManager | None = None,
    ) -> None:
        self.team = team or ITSupportTeam()
        self.service_manager = service_manager or ITServiceManager()
        self.asset_manager = asset_manager or ITAssetManager()
        self.sla_manager = sla_manager or ITSLAManager()
        self.work_orders: dict[str, ITWorkOrder] = {}

    def open(self, reference_id: str, request: str, *, asset_ids: list[str] | None = None, priority: str | None = None) -> ITWorkOrder:
        if contains_secret_request(request):
            raise ValueError("secret_request_blocked")
        workstream = classify_it_request(request)
        if workstream is None:
            text = request.lower()
            if any(term in text for term in ("production down", "outage", "all users", "business stopped")):
                workstream = "it_support"
            elif "not working" in text and any(term in text for term in ("laptop", "computer", "device")):
                workstream = "it_support"
            elif any(term in text for term in ("laptop", "computer", "printer", "device", "hardware")):
                workstream = "it_technician"
            else:
                raise ValueError("classification_required")

        ticket_type = self.service_manager.classify_ticket_type(request)
        chosen_priority = priority or self.service_manager.infer_priority(request)
        capability = {
            "it_support": "helpdesk",
            "it_technician": "endpoint_support",
            "ict": "ict",
            "mis": "mis",
        }[workstream]
        agent = self.team.select(capability)
        ticket = self.service_manager.create_ticket(
            reference_id,
            request,
            ticket_type=ticket_type,
            priority=chosen_priority,
            assigned_agent=agent,
        )
        linked = [a for a in (asset_ids or []) if self.asset_manager.get_asset(a)]
        for asset_id in linked:
            self.asset_manager.link_ticket(asset_id, ticket.ticket_id)

        sla = self.sla_manager.create_case(ticket.ticket_id, ticket.priority)
        work = ITWorkOrder(
            ticket=ticket,
            sla=sla,
            asset_ids=linked,
            workstream=workstream,
            assigned_agent=agent,
        )
        work.audit.append({"event": "work_order_opened", "ticket_id": ticket.ticket_id})
        self.work_orders[ticket.ticket_id] = work
        return work

    def authorize_action(self, ticket_id: str, action: str, *, approved: bool = False) -> dict[str, Any]:
        work = self.work_orders.get(ticket_id)
        if not work:
            return {"allowed": False, "reason": "ticket_not_found"}
        if not work.assigned_agent:
            return {"allowed": False, "reason": "agent_not_assigned"}
        decision = self.team.authorize(work.assigned_agent, action, approved=approved)
        work.approval_required = decision.requires_approval and not approved
        if work.approval_required:
            work.status = "awaiting_approval"
        elif decision.allowed:
            work.status = "action_authorized"
        work.audit.append({"event": "action_authorized" if decision.allowed else "action_denied", "action": action, "reason": decision.reason})
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "requires_approval": decision.requires_approval,
        }

    def check_sla(self, ticket_id: str, *, now=None) -> dict[str, Any]:
        work = self.work_orders.get(ticket_id)
        if not work:
            return {"found": False, "reason": "ticket_not_found"}
        result = self.sla_manager.status(work.sla, now=now)
        escalation = self.sla_manager.escalate_if_needed(work.sla, now=now)
        if escalation["escalation_required"]:
            work.status = "escalation_required"
            work.audit.append({"event": "sla_escalation_required", "reason": escalation["reason"]})
        return {"found": True, "sla": result, "escalation": escalation}

    def resolve(self, ticket_id: str, *, verified: bool) -> dict[str, Any]:
        work = self.work_orders.get(ticket_id)
        if not work:
            return {"resolved": False, "reason": "ticket_not_found"}
        ticket = self.service_manager.close_after_verification(work.ticket, verified=verified)
        if verified:
            self.sla_manager.resolve(work.sla)
            work.status = "resolved"
            work.audit.append({"event": "resolved_after_verification"})
        else:
            work.status = "open"
            work.audit.append({"event": "verification_failed"})
        return {"resolved": verified, "ticket_status": ticket.status, "verified": verified}

    def snapshot(self) -> dict[str, Any]:
        return {
            "workflow": ["classification", "ticket", "asset_link", "specialist", "sla", "approval", "verification", "resolution"],
            "credential_safe": True,
            "external_execution": "gateway_only",
            "resolution_requires_verification": True,
            "approval_gated_changes": True,
        }
