from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
import uuid


@dataclass(frozen=True)
class ITEvent:
    event_id: str
    event_type: str
    reference_id: str
    ticket_id: str | None
    payload: dict[str, Any]
    created_at: str


class ITEventBus:
    """In-process event bus with safe payload filtering and bounded dispatch."""

    BLOCKED_KEYS = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}

    def __init__(self, max_handlers_per_event: int = 8) -> None:
        self.handlers: dict[str, list[Callable[[ITEvent], None]]] = {}
        self.events: list[ITEvent] = []
        self.max_handlers_per_event = max_handlers_per_event

    @classmethod
    def _safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(k): cls._safe(v)
                for k, v in value.items()
                if str(k).lower() not in cls.BLOCKED_KEYS
            }
        if isinstance(value, list):
            return [cls._safe(v) for v in value]
        return value

    def subscribe(self, event_type: str, handler: Callable[[ITEvent], None]) -> None:
        handlers = self.handlers.setdefault(event_type, [])
        if len(handlers) >= self.max_handlers_per_event:
            raise ValueError("handler_limit_reached")
        handlers.append(handler)

    def publish(
        self,
        event_type: str,
        reference_id: str,
        *,
        ticket_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ITEvent:
        event = ITEvent(
            event_id=f"ITE-{uuid.uuid4().hex[:12].upper()}",
            event_type=event_type,
            reference_id=reference_id,
            ticket_id=ticket_id,
            payload=self._safe(payload or {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.events.append(event)
        for handler in tuple(self.handlers.get(event_type, [])):
            handler(event)
        return event

    def history(self, *, reference_id: str | None = None, ticket_id: str | None = None) -> list[ITEvent]:
        result = self.events
        if reference_id is not None:
            result = [event for event in result if event.reference_id == reference_id]
        if ticket_id is not None:
            result = [event for event in result if event.ticket_id == ticket_id]
        return list(result)

    def snapshot(self) -> dict[str, Any]:
        return {
            "event_types": sorted(self.handlers),
            "event_count": len(self.events),
            "max_handlers_per_event": self.max_handlers_per_event,
            "credentials_exposed": False,
            "external_side_effects": "handlers_must_use_gateway",
        }
