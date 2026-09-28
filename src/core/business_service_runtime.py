from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .business_function_rag import BusinessFunctionRAG
from .business_function_team import BusinessFunctionTeam
from .business_function_skills import BusinessSkillRegistry
from .business_functions import classify_business_function
from .references import ReferenceGenerator


@dataclass
class BusinessServiceState:
    request: str
    reference_id: str | None = None
    function: str | None = None
    specialist: str | None = None
    status: str = "new"
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    next_action: str | None = None
    verification_required: bool = False
    approvals_required: list[str] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    credentials_exposed: bool = False


class BusinessServiceRuntime:
    """Deterministic business-function intake, knowledge and authorization layer."""

    def __init__(self) -> None:
        self.team = BusinessFunctionTeam()
        self.skills = BusinessSkillRegistry()
        self.rag = BusinessFunctionRAG()
        self.references = ReferenceGenerator()

    def start(self, request: str) -> BusinessServiceState:
        state = BusinessServiceState(request=request.strip())
        state.reference_id = self.references.next("BIZ")
        self._audit(state, "request_received")

        function = classify_business_function(request)
        if not function:
            state.status = "clarification_required"
            state.next_action = "Ask one focused question to identify the business function."
            self._audit(state, "function_ambiguous")
            return state

        specialist = self.team.select(function)
        if not specialist:
            state.status = "specialist_unavailable"
            state.next_action = "Escalate for human review."
            self._audit(state, "specialist_unavailable")
            return state

        state.function = function
        state.specialist = specialist
        state.active_skills = self.skills.skills_for(function)
        state.knowledge = self.rag.provenance(self.rag.search(request, function=function))
        state.status = "triaged"
        state.next_action = "Use approved knowledge, perform bounded analysis, then verify."
        state.verification_required = True
        self._audit(state, "request_triaged", function=function, specialist=specialist)
        return state

    def authorize_action(
        self,
        state: BusinessServiceState,
        action: str,
        *,
        approved: bool = False,
    ) -> dict[str, Any]:
        if not state.specialist:
            return {"allowed": False, "reason": "no_specialist", "requires_approval": False}
        decision = self.team.authorize(state.specialist, action, approved=approved)
        if decision.requires_approval and not approved:
            state.status = "awaiting_approval"
            state.approvals_required.append(action)
        elif decision.allowed:
            state.status = "action_authorized"
        self._audit(
            state,
            "action_authorization",
            action=action,
            allowed=decision.allowed,
            reason=decision.reason,
        )
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "requires_approval": decision.requires_approval,
        }

    @staticmethod
    def _audit(state: BusinessServiceState, event: str, **details: Any) -> None:
        state.audit.append({"event": event, "details": details})

    def snapshot(self) -> dict[str, Any]:
        return {
            "runtime": "business_service",
            "specialist_count": self.team.snapshot()["specialist_count"],
            "skill_count": self.skills.snapshot()["skill_count"],
            "knowledge_provider": self.rag.snapshot()["provider"],
            "provenance": True,
            "approval_gates": True,
            "verification_required": True,
            "credentials_exposed_to_agents": False,
            "production_access": "gateway_only",
        }
