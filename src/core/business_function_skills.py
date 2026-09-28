from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class BusinessSkillDecision:
    skill: str
    allowed: bool
    reason: str
    human_review: bool


class BusinessSkillRegistry:
    """Bounded skill registry; skills cannot exceed declared function/action scope."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "config" / "business_function_skills.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    def get(self, skill: str) -> dict[str, Any] | None:
        return self.data.get("skills", {}).get(skill)

    def exists(self, skill: str) -> bool:
        return self.get(skill) is not None

    def skills_for(self, function: str) -> list[str]:
        return sorted(
            skill
            for skill, cfg in self.data.get("skills", {}).items()
            if function in cfg.get("allowed_functions", [])
        )

    def authorize(
        self,
        skill: str,
        function: str,
        action: str,
    ) -> BusinessSkillDecision:
        cfg = self.get(skill)
        if not cfg:
            return BusinessSkillDecision(skill, False, "unknown_skill", False)
        if function not in cfg.get("allowed_functions", []):
            return BusinessSkillDecision(skill, False, "function_scope_denied", False)
        if action not in cfg.get("actions", []):
            return BusinessSkillDecision(skill, False, "action_scope_denied", False)
        return BusinessSkillDecision(
            skill,
            True,
            "allowed",
            bool(cfg.get("human_review", False)),
        )

    def select(self, function: str, requested_action: str | None = None) -> list[str]:
        skills = self.skills_for(function)
        if requested_action:
            skills = [
                skill for skill in skills
                if requested_action in self.get(skill).get("actions", [])
            ]
        return skills

    def snapshot(self) -> dict[str, Any]:
        policy = self.data.get("policy", {})
        return {
            "skill_count": len(self.data.get("skills", {})),
            "skills": sorted(self.data.get("skills", {})),
            "default_action": policy.get("default_action", "deny"),
            "credentials_exposed_to_agents": False,
            "production_access": policy.get("production_access", "gateway_only"),
            "audit_required": policy.get("every_skill_execution", "audit"),
        }
