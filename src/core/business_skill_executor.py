from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .business_function_team import BusinessFunctionTeam
from .business_function_skills import BusinessSkillRegistry
from .business_function_rag import BusinessFunctionRAG


@dataclass(frozen=True)
class BusinessSkillExecution:
    function: str
    specialist: str
    skill: str
    action: str
    allowed: bool
    status: str
    reason: str
    human_review: bool
    knowledge: list[dict[str, Any]]
    gateway_required: bool
    credentials_exposed: bool


class BusinessSkillExecutor:
    """Validate and plan bounded specialist skill execution before any gateway/tool call."""

    def __init__(
        self,
        team: BusinessFunctionTeam | None = None,
        skills: BusinessSkillRegistry | None = None,
        rag: BusinessFunctionRAG | None = None,
    ) -> None:
        self.team = team or BusinessFunctionTeam()
        self.skills = skills or BusinessSkillRegistry()
        self.rag = rag or BusinessFunctionRAG()

    def execute_plan(
        self,
        *,
        function: str,
        specialist: str,
        skill: str,
        action: str,
        request: str,
        approved: bool = False,
    ) -> BusinessSkillExecution:
        specialist_cfg = self.team.get(specialist)
        if not specialist_cfg:
            return self._denied(function, specialist, skill, action, "unknown_specialist")
        if specialist_cfg.get("function") != function:
            return self._denied(function, specialist, skill, action, "specialist_function_mismatch")

        decision = self.skills.authorize(skill, function, action)
        if not decision.allowed:
            return self._denied(function, specialist, skill, action, decision.reason)

        if decision.human_review and not approved:
            status = "awaiting_approval"
            reason = "human_review_required"
        else:
            status = "planned"
            reason = "skill_execution_authorized"

        knowledge = self.rag.provenance(self.rag.search(request, function=function))
        return BusinessSkillExecution(
            function=function,
            specialist=specialist,
            skill=skill,
            action=action,
            allowed=True,
            status=status,
            reason=reason,
            human_review=decision.human_review,
            knowledge=knowledge,
            gateway_required=action not in {"inspect", "analyze", "plan", "research", "report", "advise", "document", "validate", "test"},
            credentials_exposed=False,
        )

    @staticmethod
    def _denied(function: str, specialist: str, skill: str, action: str, reason: str) -> BusinessSkillExecution:
        return BusinessSkillExecution(
            function=function,
            specialist=specialist,
            skill=skill,
            action=action,
            allowed=False,
            status="denied",
            reason=reason,
            human_review=False,
            knowledge=[],
            gateway_required=False,
            credentials_exposed=False,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "execution": "bounded_skill_plan",
            "rag_provenance": True,
            "gateway_required_for_external_actions": True,
            "credentials_exposed_to_agents": False,
            "external_provider_calls": False,
        }
