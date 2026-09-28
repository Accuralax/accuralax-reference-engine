from __future__ import annotations

from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class PeopleOrganisation:
    """Governed workforce, organisational structure and HR intelligence."""

    def __init__(self) -> None:
        self.people: dict[str, dict[str, Any]] = {}
        self.teams: dict[str, dict[str, Any]] = {}
        self.roles: dict[str, dict[str, Any]] = {}
        self.assignments: list[dict[str, Any]] = []
        self.reviews: list[dict[str, Any]] = []
        self.leave_requests: list[dict[str, Any]] = []
        self.hr_cases: list[dict[str, Any]] = []
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_person(self, name: str, role: str) -> dict[str, Any]:
        person_id = f"PER-{uuid.uuid4().hex[:10].upper()}"
        item = {"person_id": person_id, "name": name, "role": role, "status": "active"}
        self.people[person_id] = item
        self.lineage.record("person.created", "system", "person", person_id, "people")
        return self._safe(item)

    def create_team(self, name: str, department: str) -> dict[str, Any]:
        team_id = f"TEAM-{uuid.uuid4().hex[:10].upper()}"
        item = {"team_id": team_id, "name": name, "department": department, "status": "active"}
        self.teams[team_id] = item
        return self._safe(item)

    def define_role(self, name: str, permissions: list[str]) -> dict[str, Any]:
        role_id = f"ROLE-{uuid.uuid4().hex[:10].upper()}"
        item = {"role_id": role_id, "name": name, "permissions": permissions}
        self.roles[role_id] = item
        return self._safe(item)

    def assign(self, person_id: str, team_id: str, responsibility: str) -> dict[str, Any]:
        if person_id not in self.people or team_id not in self.teams:
            return {"allowed": False, "reason": "person_or_team_not_found"}
        item = {"assignment_id": f"ASN-{uuid.uuid4().hex[:10].upper()}",
                "person_id": person_id, "team_id": team_id,
                "responsibility": responsibility, "status": "active"}
        self.assignments.append(item)
        return self._safe(item)

    def request_leave(self, person_id: str, start: str, end: str) -> dict[str, Any]:
        if person_id not in self.people:
            return {"allowed": False, "reason": "person_not_found"}
        item = {"leave_id": f"LV-{uuid.uuid4().hex[:10].upper()}",
                "person_id": person_id, "start": start, "end": end, "status": "pending"}
        self.leave_requests.append(item)
        return self._safe(item)

    def approve_leave(self, leave_id: str, approved: bool = False) -> dict[str, Any]:
        leave = next((x for x in self.leave_requests if x["leave_id"] == leave_id), None)
        if not leave:
            return {"allowed": False, "reason": "leave_not_found"}
        decision = self.policy.evaluate("leave_approval", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        leave["status"] = "approved"
        return {"allowed": True, "leave_id": leave_id, "status": "approved"}

    def create_performance_review(self, person_id: str, summary: str) -> dict[str, Any]:
        if person_id not in self.people:
            return {"allowed": False, "reason": "person_not_found"}
        item = {"review_id": f"REV-{uuid.uuid4().hex[:10].upper()}",
                "person_id": person_id, "summary": summary, "status": "draft"}
        self.reviews.append(item)
        return self._safe(item)

    def create_hr_case(self, person_id: str, category: str, summary: str,
                       approved: bool = False) -> dict[str, Any]:
        if person_id not in self.people:
            return {"allowed": False, "reason": "person_not_found"}
        decision = self.policy.evaluate("sensitive_hr_decision", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item = {"case_id": f"HR-{uuid.uuid4().hex[:10].upper()}",
                "person_id": person_id, "category": category,
                "summary": summary, "status": "open"}
        self.hr_cases.append(item)
        return self._safe(item)

    def workforce_intelligence(self) -> dict[str, Any]:
        return {"people": len(self.people), "teams": len(self.teams),
                "roles": len(self.roles), "assignments": len(self.assignments),
                "pending_leave": sum(x["status"] == "pending" for x in self.leave_requests),
                "open_hr_cases": sum(x["status"] == "open" for x in self.hr_cases)}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", **self.workforce_intelligence(),
                "reviews": len(self.reviews), "credentials_exposed": False,
                "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): PeopleOrganisation._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [PeopleOrganisation._safe(v) for v in value]
        return value
