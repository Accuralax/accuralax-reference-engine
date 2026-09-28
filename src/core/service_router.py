from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ServiceMatch:
    area_id: str
    area_name: str
    service_id: str | None
    service_name: str | None
    score: int


class ServiceRouter:
    """Deterministic first-pass service routing with ambiguity protection."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "services.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def route(self, request: str) -> ServiceMatch | None:
        text = request.lower()
        candidates: list[ServiceMatch] = []

        for service in self.data.get("services", []):
            keywords = service.get("keywords", [])
            score = sum(1 for keyword in keywords if keyword.lower() in text)

            boosts = {
                "business_registration": ("register my business", "business registration", "register a business"),
                "funding_proposal": ("funding", "grant", "funding proposal", "funding for my business"),
                "ai_automation": ("ai automation", "automate", "automation", "ai agent", "ai assistant"),
                "cybersecurity": ("cybersecurity", "cyber security", "security incident", "data protection"),
            }
            if any(x in text for x in boosts.get(service["id"], ())):
                score += 6

            if score <= 0:
                continue

            area = next((a for a in self.data.get("service_areas", []) if a["id"] == service["area"]), None)
            if area:
                candidates.append(ServiceMatch(area["id"], area["name"], service["id"], service["name"], score))

        if not candidates:
            return self._area_match(text)

        candidates.sort(key=lambda item: item.score, reverse=True)
        if len(candidates) > 1 and candidates[0].score == candidates[1].score:
            return None
        return candidates[0]

    def _area_match(self, text: str) -> ServiceMatch | None:
        candidates = []
        for area in self.data.get("service_areas", []):
            score = sum(1 for keyword in area.get("keywords", []) if keyword.lower() in text)
            if score:
                candidates.append(ServiceMatch(area["id"], area["name"], None, None, score))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.score, reverse=True)
        if len(candidates) > 1 and candidates[0].score == candidates[1].score:
            return None
        return candidates[0]
