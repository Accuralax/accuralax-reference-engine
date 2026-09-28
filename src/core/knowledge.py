from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class KnowledgeBase:
    """Local, auditable service knowledge loaded from YAML."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "service_knowledge.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, service_id: str) -> dict[str, Any] | None:
        return self.data.get("knowledge", {}).get(service_id)

    def intake_fields(self, service_id: str) -> tuple[str, ...]:
        item = self.get(service_id)
        return tuple(item.get("intake", ())) if item else ()

    def response_rules(self, service_id: str) -> tuple[str, ...]:
        item = self.get(service_id)
        return tuple(item.get("response_rules", ())) if item else ()

    def handoff(self, service_id: str) -> str | None:
        item = self.get(service_id)
        return item.get("handoff") if item else None

    def unknown_service_policy(self) -> dict[str, Any]:
        return self.data.get("routing", {}).get("unknown_service", {})
