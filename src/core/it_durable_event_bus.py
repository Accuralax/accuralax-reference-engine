from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .it_event_bus import ITEvent, ITEventBus
from .it_persistent_store import ITPersistentStore


class DurableITEventBus:
    """Persistent event bus with bounded in-process delivery."""

    def __init__(
        self,
        *,
        event_store: ITPersistentStore | None = None,
        bus: ITEventBus | None = None,
    ) -> None:
        self.event_store = event_store or ITPersistentStore()
        self.bus = bus or ITEventBus()

    def subscribe(self, event_type: str, handler: Callable[[ITEvent], None]) -> None:
        self.bus.subscribe(event_type, handler)

    def publish(
        self,
        event_type: str,
        reference_id: str,
        *,
        ticket_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ITEvent:
        event = self.bus.publish(
            event_type,
            reference_id,
            ticket_id=ticket_id,
            payload=payload,
        )
        self.event_store.record(
            reference_id,
            event_type,
            {
                "event_id": event.event_id,
                "payload": event.payload,
                "created_at": event.created_at,
            },
            ticket_id=ticket_id,
        )
        return event

    def durable_history(
        self,
        reference_id: str,
        *,
        ticket_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.event_store.list_events(reference_id, ticket_id=ticket_id)

    def replay(
        self,
        reference_id: str,
        *,
        ticket_id: str | None = None,
        event_types: set[str] | None = None,
    ) -> list[ITEvent]:
        """Rehydrate matching durable events into the bounded local bus."""
        rows = self.event_store.list_events(reference_id, ticket_id=ticket_id)
        replayed: list[ITEvent] = []
        for row in rows:
            if event_types and row["event_type"] not in event_types:
                continue
            payload = row["details"].get("payload", {})
            event = self.bus.publish(
                row["event_type"],
                row["reference_id"],
                ticket_id=row["ticket_id"],
                payload=payload,
            )
            replayed.append(event)
        return replayed

    def snapshot(self) -> dict[str, Any]:
        snapshot = self.bus.snapshot()
        snapshot.update({
            "durable": True,
            "replay_supported": True,
            "persistent_event_store": str(self.event_store.path),
            "credentials_exposed": False,
        })
        return snapshot
