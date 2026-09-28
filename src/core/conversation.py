from __future__ import annotations

from dataclasses import dataclass, field

from .knowledge import KnowledgeBase
from .references import reference_generator
from .service_router import ServiceRouter


@dataclass
class ConversationState:
    request: str
    reference_id: str = field(default_factory=lambda: reference_generator.next("ENQ"))
    service_id: str | None = None
    service_name: str | None = None
    required_fields: tuple[str, ...] = ()
    collected: dict[str, str] = field(default_factory=dict)
    consent_given: bool = False
    owner_assigned: bool = False
    status: str = "intake"

    @property
    def missing_information(self) -> tuple[str, ...]:
        return tuple(field for field in self.required_fields if not self.collected.get(field))


class ConversationEngine:
    """Deterministic multi-turn intake and handoff orchestration."""

    def __init__(self) -> None:
        self.router = ServiceRouter()
        self.knowledge = KnowledgeBase()

    def start(self, request: str) -> ConversationState:
        state = ConversationState(request=request.strip())
        match = self.router.route(state.request)

        if not match or not match.service_id:
            state.status = "clarification_required"
            return state

        state.service_id = match.service_id
        state.service_name = match.service_name
        state.required_fields = self.knowledge.intake_fields(state.service_id)
        state.status = "information_required" if state.missing_information else "intake_complete"
        return state

    def record_information(self, state: ConversationState, field: str, value: str) -> ConversationState:
        if field not in state.required_fields:
            raise ValueError(f"Field {field!r} is not required for this service.")
        value = value.strip()
        if not value:
            raise ValueError("Intake value cannot be empty.")
        state.collected[field] = value
        state.status = "intake_complete" if not state.missing_information else "information_required"
        return state

    def next_missing_field(self, state: ConversationState) -> str | None:
        return state.missing_information[0] if state.missing_information else None

    def record_consent(self, state: ConversationState, consent: bool) -> ConversationState:
        state.consent_given = bool(consent)
        state.status = "handoff_ready" if state.consent_given else "consent_required"
        return state

    def assign_owner(self, state: ConversationState) -> ConversationState:
        if not state.consent_given:
            state.status = "consent_required"
            return state
        if state.missing_information:
            state.status = "information_required"
            return state
        state.owner_assigned = True
        state.status = "handoff_complete"
        return state
