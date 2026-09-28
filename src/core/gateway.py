from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .orchestrator import ConversationOrchestrator


class AgentGateway:
    """Transport-neutral message boundary for WhatsApp, Make, web, or other adapters."""

    def __init__(self, orchestrator: ConversationOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or ConversationOrchestrator()

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action", "start")).strip().lower()

        if action == "start":
            request = str(payload.get("message", "")).strip()
            if not request:
                raise ValueError("message is required")
            result = self.orchestrator.start(request)

        elif action == "information":
            result = self.orchestrator.continue_with_information(
                str(payload.get("reference_id", "")),
                str(payload.get("field", "")),
                str(payload.get("value", "")),
            )

        elif action == "consent":
            result = self.orchestrator.continue_with_consent(
                str(payload.get("reference_id", "")),
                bool(payload.get("consent", False)),
            )

        elif action == "handoff":
            result = self.orchestrator.assign_owner(str(payload.get("reference_id", "")))

        elif action == "status":
            result = self.orchestrator.get(str(payload.get("reference_id", "")))

        else:
            raise ValueError(f"Unsupported action: {action!r}")

        return {
            "reference_id": result.state.reference_id,
            "status": result.state.status,
            "service_id": result.state.service_id,
            "service_name": result.state.service_name,
            "missing_information": list(result.state.missing_information),
            "consent_given": result.state.consent_given,
            "owner_assigned": result.state.owner_assigned,
            "agent_context": result.agent_context,
        }
