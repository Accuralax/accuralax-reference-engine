from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


@dataclass
class Project:
    project_id: str
    name: str
    status: str = "draft"
    tasks: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    budget: float = 0.0


class ProjectPortfolio:
    """Governed project, programme and portfolio management intelligence."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.portfolios: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, dict[str, Any]] = {}
        self.milestones: dict[str, dict[str, Any]] = {}
        self.risks: list[dict[str, Any]] = []
        self.lineage = EventLineage()
        self.policy = GovernanceEngine()

    def create_project(self, name: str, budget: float = 0.0) -> dict[str, Any]:
        project_id = f"PRJ-{uuid.uuid4().hex[:10].upper()}"
        self.projects[project_id] = Project(project_id, name, budget=budget)
        self.lineage.record("project.created", "system", "project", project_id, "portfolio")
        return self._safe({"project_id": project_id, "name": name, "status": "draft", "budget": budget})

    def activate_project(self, project_id: str, approved: bool = False) -> dict[str, Any]:
        project = self.projects.get(project_id)
        if not project:
            return {"allowed": False, "reason": "project_not_found"}
        decision = self.policy.evaluate("project_activation", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        project.status = "active"
        self.lineage.record("project.activated", "operator", "project", project_id, "portfolio")
        return {"allowed": True, "project_id": project_id, "status": "active"}

    def add_task(self, project_id: str, title: str) -> dict[str, Any]:
        project = self.projects.get(project_id)
        if not project:
            return {"allowed": False, "reason": "project_not_found"}
        task_id = f"TASK-{uuid.uuid4().hex[:10].upper()}"
        self.tasks[task_id] = {"task_id": task_id, "project_id": project_id,
                               "title": title, "status": "backlog"}
        project.tasks.append(task_id)
        return self._safe(self.tasks[task_id])

    def add_milestone(self, project_id: str, name: str) -> dict[str, Any]:
        project = self.projects.get(project_id)
        if not project:
            return {"allowed": False, "reason": "project_not_found"}
        milestone_id = f"MS-{uuid.uuid4().hex[:10].upper()}"
        self.milestones[milestone_id] = {"milestone_id": milestone_id,
                                         "project_id": project_id,
                                         "name": name, "status": "planned"}
        project.milestones.append(milestone_id)
        return self._safe(self.milestones[milestone_id])

    def add_dependency(self, project_id: str, dependency: str) -> dict[str, Any]:
        project = self.projects.get(project_id)
        if not project:
            return {"allowed": False, "reason": "project_not_found"}
        project.dependencies.append(dependency)
        return {"project_id": project_id, "dependency": dependency}

    def add_risk(self, project_id: str, risk: str, severity: str = "medium") -> dict[str, Any]:
        if project_id not in self.projects:
            return {"allowed": False, "reason": "project_not_found"}
        item = {"risk_id": f"RSK-{uuid.uuid4().hex[:10].upper()}",
                "project_id": project_id, "risk": risk, "severity": severity,
                "status": "open"}
        self.risks.append(item)
        return self._safe(item)

    def portfolio_health(self) -> dict[str, Any]:
        active = sum(p.status == "active" for p in self.projects.values())
        blocked = sum(p.status == "blocked" for p in self.projects.values())
        risk_count = len(self.risks)
        status = "red" if blocked else ("amber" if risk_count else "green")
        return {"status": status, "projects": len(self.projects), "active": active,
                "blocked": blocked, "open_risks": risk_count,
                "confidence": "observed" if self.projects else "low",
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "projects": len(self.projects),
                "tasks": len(self.tasks), "milestones": len(self.milestones),
                "risks": len(self.risks), "credentials_exposed": False,
                "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ProjectPortfolio._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ProjectPortfolio._safe(v) for v in value]
        return value
