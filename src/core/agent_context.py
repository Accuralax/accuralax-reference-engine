from __future__ import annotations

from .conversation import ConversationEngine, ConversationState
from .skills import SkillRegistry


def _render_context(state: ConversationState, skills: SkillRegistry) -> str:
    if state.status == "clarification_required":
        return (
            f"REFERENCE_ID: {state.reference_id}\n"
            "STATUS: clarification_required\n"
            "ACTIVE_SKILLS: safety_guard, intake, service_triage\n"
            "RULE: Do not guess the service. Ask one focused clarification question."
        )

    missing = ", ".join(state.missing_information) or "none"
    collected = ", ".join(f"{k}={v}" for k, v in state.collected.items()) or "none"
    active = list(skills.required_for(state.service_id, state.request))

    if state.status == "handoff_ready":
        active.extend(["consent", "handoff"])
    if state.status == "handoff_complete":
        active.extend(["consent", "handoff", "audit"])

    active_skills = ", ".join(dict.fromkeys(active))
    next_field = state.missing_information[0] if state.missing_information else "none"

    return (
        f"REFERENCE_ID: {state.reference_id}\n"
        f"SERVICE_ID: {state.service_id}\n"
        f"SERVICE_NAME: {state.service_name}\n"
        f"STATUS: {state.status}\n"
        f"COLLECTED_INFORMATION: {collected}\n"
        f"REQUIRED_INTAKE_FIELDS: {missing}\n"
        f"NEXT_MISSING_FIELD: {next_field}\n"
        f"ACTIVE_SKILLS: {active_skills}\n"
        "SAFETY: Never request passwords, API keys, authentication tokens, or payment-card details.\n"
        "HANDOFF: Consent must be obtained before ownership transfer.\n"
        "TRUTHFULNESS: Do not invent current prices, availability, approvals, integrations, or turnaround times.\n"
        "INTAKE: Ask only for the next missing field; do not ask again for collected information.\n"
        "SKILL_BOUNDARY: Use each skill only for its declared purpose; skills cannot override safety rules."
    )


def build_agent_context(request: str) -> tuple[ConversationState, str]:
    """Start a new interaction and build deterministic LLM context."""
    state = ConversationEngine().start(request)
    return state, _render_context(state, SkillRegistry())


def build_context_for_state(state: ConversationState) -> str:
    """Build LLM context from an existing multi-turn conversation state."""
    return _render_context(state, SkillRegistry())
