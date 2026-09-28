from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import uuid

import yaml


@dataclass(frozen=True)
class LineageEvent:
    event_id: str
    event_type: str
    actor_id: str
    entity_type: str
    entity_id: str
    occurred_at: str
    source: str
    details: dict[str, Any]


class EventLineage:
    """Append-only event and data-lineage recorder with secret-safe details."""

    BLOCKED = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}

    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "event_lineage.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.events: list[LineageEvent] = []

    @staticmethod
    def hash_value(value: Any) -> str:
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    @classmethod
    def _safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): cls._safe(v) for k, v in value.items()
                    if str(k).lower() not in cls.BLOCKED}
        if isinstance(value, list):
            return [cls._safe(v) for v in value]
        return value

    def record(self, event_type: str, actor_id: str, entity_type: str,
               entity_id: str, source: str, **details: Any) -> LineageEvent:
        event = LineageEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            details=self._safe(details),
        )
        self.events.append(event)
        return event

    def lineage(self, entity_id: str) -> list[dict[str, Any]]:
        return [asdict(e) for e in self.events if e.entity_id == entity_id]

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "event_count": len(self.events),
                "append_only": True, "credentials_recorded": False}
