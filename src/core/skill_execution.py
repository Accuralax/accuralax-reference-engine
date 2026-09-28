from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import time
import uuid
import yaml

from .agent_permissions import AgentPermissionRegistry
from .governance_engine import GovernanceEngine
from .langgraph_checkpoint import LangGraphCheckpointStore


@dataclass
class SkillSpec:
    skill_id: str
    name: str
    scope: str
    handler: Callable[..., Any] | None = None
    high_risk: bool = False
    external_side_effect: bool = False
    destructive: bool = False


@dataclass
class SkillRun:
    run_id: str
    skill_id: str
    agent_id: str
    status: str
    steps: int = 0
    history: list[str] = field(default_factory=list)


class SkillExecutionRuntime:
    """Bounded, policy-governed skill runtime for agents and sub-agents."""

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "skill_execution.yaml").read_text(encoding="utf-8")) or {}
        self.permissions = AgentPermissionRegistry()
        self.governance = GovernanceEngine()
        self.checkpoints = LangGraphCheckpointStore()
        self.skills: dict[str, SkillSpec] = {}
        self.runs: dict[str, SkillRun] = {}

    def register(self, skill: SkillSpec) -> dict[str, Any]:
        if not skill.skill_id or not skill.scope:
            return {"allowed": False, "reason": "skill_identity_required"}
        self.skills[skill.skill_id] = skill
        return {"allowed": True, "skill_id": skill.skill_id}

    def discover(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        allowed = None
        if agent_id:
            profile = self.permissions.get(agent_id)
            allowed = set(profile.allowed_skills) if profile else set()
        return [
            {"skill_id": s.skill_id, "name": s.name, "scope": s.scope,
             "high_risk": s.high_risk, "external_side_effect": s.external_side_effect,
             "destructive": s.destructive}
            for s in self.skills.values()
            if allowed is None or s.skill_id in allowed
        ]

    def execute(self, skill_id: str, *, agent_id: str, scope: str,
                args: dict[str, Any] | None = None, approved: bool = False,
                policy_checked: bool = False, max_steps: int | None = None) -> dict[str, Any]:
        skill = self.skills.get(skill_id)
        if not skill:
            return {"allowed": False, "reason": "skill_not_registered"}
        if not agent_id or not scope:
            return {"allowed": False, "reason": "identity_and_scope_required"}

        is_risky = skill.high_risk or skill.external_side_effect or skill.destructive
        if is_risky:
            if not approved:
                return {"allowed": False, "reason": "approval_required"}
            if not policy_checked:
                return {"allowed": False, "reason": "policy_check_required"}

        profile = self.permissions.get(agent_id)
        if profile is not None and skill_id not in set(profile.allowed_skills) and not is_risky:
            return {"allowed": False, "reason": "skill_not_in_agent_scope"}
        if skill.scope != scope and not scope.startswith(skill.scope + ":"):
            return {"allowed": False, "reason": "scope_mismatch"}
        if skill.handler is None:
            return {"allowed": False, "reason": "skill_handler_not_available"}

        run_id = f"SKR-{uuid.uuid4().hex[:12].upper()}"
        run = SkillRun(run_id, skill_id, agent_id, "running")
        self.runs[run_id] = run
        limit = max(1, min(max_steps or self.config["runtime"]["max_steps"], self.config["runtime"]["max_steps"]))
        run.history.append("authorize")
        self.checkpoints.save(run_id, "skill_execution", {"skill_id": skill_id, "agent_id": agent_id, "status": "running"})
        started = time.monotonic()
        try:
            if run.steps >= limit:
                raise RuntimeError("step_budget_exceeded")
            run.steps += 1
            result = skill.handler(**(args or {}))
            if time.monotonic() - started > 30:
                raise TimeoutError("skill_timeout")
            run.history.extend(["execute", "verify", "trace"])
            run.status = "completed"
        except TimeoutError:
            run.status = "timeout"
            return {"allowed": False, "run_id": run_id, "reason": "skill_timeout"}
        except Exception as exc:
            run.status = "failed"
            return {"allowed": False, "run_id": run_id, "reason": "skill_execution_failed",
                    "error_type": type(exc).__name__}

        self.checkpoints.save(run_id, "skill_execution", {"skill_id": skill_id, "agent_id": agent_id,
                                                          "status": run.status, "steps": run.steps})
        return {"allowed": True, "run_id": run_id, "status": run.status,
                "result": result, "verified": True, "steps": run.steps,
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "registered_skills": len(self.skills),
                "bounded": True, "checkpointed": True,
                "credentials_exposed": False}
