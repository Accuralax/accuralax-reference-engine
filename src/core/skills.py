from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SkillRegistry:
    """Load and validate the local CyberFusion skill catalogue."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "skills.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, skill_id: str) -> dict[str, Any] | None:
        return self.data.get("skills", {}).get(skill_id)

    def available(self) -> tuple[str, ...]:
        return tuple(self.data.get("skills", {}).keys())

    def required_for(self, service_id: str | None, request: str = "") -> tuple[str, ...]:
        text = request.lower()
        selected = ["safety_guard", "intake", "service_triage", "knowledge_lookup"]

        if service_id in {"ai_automation", "website", "software_app"}:
            selected.append("proposal_scoping")
        if service_id == "cybersecurity" or any(
            word in text for word in ("cybersecurity", "cyber attack", "security incident")
        ):
            selected.append("cybersecurity_triage")

        return tuple(dict.fromkeys(selected))

    def execution_order(self) -> tuple[str, ...]:
        return tuple(self.data.get("execution", {}).get("order", ()))
