from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    reference_id: str
    event_type: str
    actor: str
    details: dict[str, Any]
    timestamp: str


def create_audit_event(
    reference_id: str,
    event_type: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a JSON-serializable audit event; secrets must never be placed in details."""
    return asdict(AuditEvent(
        reference_id=reference_id,
        event_type=event_type,
        actor=actor,
        details=details or {},
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))
