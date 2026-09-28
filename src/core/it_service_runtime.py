from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .it_support_team import ITSupportTeam, classify_it_request, contains_secret_request
from .references import ReferenceGenerator
from .it_support_rag import ITSupportRAG

@dataclass
class ITServiceState:
    request: str
    reference_id: str | None = None
    status: str = "new"
    workstreams: list[str] = field(default_factory=list)
    selected_agents: dict[str, str] = field(default_factory=dict)
    next_action: str | None = None
    approvals_required: list[str] = field(default_factory=list)
    verification_required: bool = False
    audit: list[dict[str, Any]] = field(default_factory=list)
    credentials_exposed: bool = False

class ITServiceRuntime:
    """Deterministic IT service layer before LLM reasoning or external tools."""
    def __init__(self, team: ITSupportTeam | None = None) -> None:
        self.team = team or ITSupportTeam()
        self.references = ReferenceGenerator()
        self.rag = ITSupportRAG()

    def start(self, request: str) -> ITServiceState:
        state = ITServiceState(request=request.strip())
        state.reference_id = self.references.next("IT")
        self._audit(state, "request_received")
        if contains_secret_request(request):
            state.status = "blocked_security"
            state.next_action = "Do not collect credentials; provide a safe support path."
            self._audit(state, "secret_request_blocked")
            return state
        stream = classify_it_request(request)
        if stream is None:
            state.status = "clarification_required"
            state.next_action = "Ask one focused question to identify support, technician, ICT, or MIS work."
            self._audit(state, "classification_ambiguous")
            return state
        state.workstreams = [stream]
        capability = {"it_support": "helpdesk", "it_technician": "endpoint_support", "ict": "ict", "mis": "mis"}[stream]
        agent = self.team.select(capability)
        if agent:
            state.selected_agents[stream] = agent
        state.status = "triaged"
        state.next_action = "Diagnose and verify before making changes."
        state.verification_required = True
        self._audit(state, "request_triaged")
        return state

    def retrieve_knowledge(self, request: str, domain: str | None = None) -> list[dict[str, Any]]:
        return self.rag.provenance(self.rag.search(request, domain=domain))

    def authorize_action(self, state: ITServiceState, action: str, *, approved: bool = False) -> dict[str, Any]:
        if not state.workstreams:
            return {"allowed": False, "reason": "no_workstream"}
        agent = state.selected_agents.get(state.workstreams[0])
        if not agent:
            return {"allowed": False, "reason": "no_agent"}
        decision = self.team.authorize(agent, action, approved=approved)
        if decision.requires_approval and not approved:
            state.status = "awaiting_approval"
            state.approvals_required.append(action)
        elif decision.allowed:
            state.status = "action_authorized"
        self._audit(state, "action_authorization", action=action, allowed=decision.allowed, reason=decision.reason)
        return {"allowed": decision.allowed, "reason": decision.reason, "requires_approval": decision.requires_approval}

    @staticmethod
    def _audit(state: ITServiceState, event: str, **details: Any) -> None:
        state.audit.append({"event": event, "details": details})

    def snapshot(self) -> dict[str, Any]:
        return {"runtime": "it_service", "agents": sorted(self.team.data.get("agents", {})), "credentials_exposed_to_agents": False, "production_access": "gateway_only", "approval_gates": True, "verification_required": True}
