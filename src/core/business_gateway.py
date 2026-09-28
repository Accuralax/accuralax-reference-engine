from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    reason: str
    system: str
    action: str


class BusinessCapabilityGateway:
    """Provider-neutral gateway for external business systems.

    Agents see capabilities such as `hubspot.search_contact`, not provider
    credentials or raw API clients. Provider adapters belong behind this gate.
    """

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "business_systems.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def is_allowed(self, system: str, action: str) -> bool:
        item = self.data.get("systems", {}).get(system)
        return bool(item and action in item.get("actions", []))

    def is_side_effect(self, system: str, action: str) -> bool:
        item = self.data.get("systems", {}).get(system)
        return bool(item and action in item.get("side_effects", []))

    def authorize(self, system: str, action: str, *, approved: bool = False, idempotency_key: str | None = None) -> CapabilityDecision:
        if not self.is_allowed(system, action):
            return CapabilityDecision(False, "capability_denied", system, action)
        if self.is_side_effect(system, action):
            if not idempotency_key:
                return CapabilityDecision(False, "idempotency_key_required", system, action)
            if not approved:
                return CapabilityDecision(False, "approval_required_for_side_effect", system, action)
        return CapabilityDecision(True, "capability_allowed", system, action)

    def describe(self, system: str) -> dict[str, Any]:
        return dict(self.data.get("systems", {}).get(system, {}))
