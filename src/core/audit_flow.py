from __future__ import annotations

from typing import Any

from .audit import create_audit_event
from .conversation import ConversationState


def audit_state(state: ConversationState, event_type: str, actor: str = "system") -> dict[str, Any]:
    return create_audit_event(
        reference_id=state.reference_id,
        event_type=event_type,
        actor=actor,
        details={
            "status": state.status,
            "service_id": state.service_id,
            "consent_given": state.consent_given,
            "owner_assigned": state.owner_assigned,
        },
    )
