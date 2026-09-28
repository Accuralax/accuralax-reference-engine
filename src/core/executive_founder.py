from __future__ import annotations

from typing import Any
import uuid

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class ExecutiveFounder:
    """Governed executive and founder-office intelligence."""

    def __init__(self) -> None:
        self.priorities: dict[str, dict[str, Any]] = {}
        self.decisions: list[dict[str, Any]] = []
        self.board_matters: list[dict[str, Any]] = []
        self.briefs: list[dict[str, Any]] = []
        self.approvals: list[dict[str, Any]] = []
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_priority(self, title: str, owner: str) -> dict[str, Any]:
        item = {"priority_id": f"PRI-{uuid.uuid4().hex[:10].upper()}",
                "title": title, "owner": owner, "status": "proposed"}
        self.priorities[item["priority_id"]] = item
        self.lineage.record("priority.created", owner, "strategic_priority",
                            item["priority_id"], "executive")
        return self._safe(item)

    def activate_priority(self, priority_id: str, approved: bool = False) -> dict[str, Any]:
        item = self.priorities.get(priority_id)
        if not item:
            return {"allowed": False, "reason": "priority_not_found"}
        decision = self.policy.evaluate("strategic_decision", approved=approved)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item["status"] = "active"
        return {"allowed": True, "priority_id": priority_id, "status": "active"}

    def create_decision(self, title: str, options: list[str]) -> dict[str, Any]:
        item = {"decision_id": f"DEC-{uuid.uuid4().hex[:10].upper()}",
                "title": title, "options": options, "status": "pending"}
        self.decisions.append(item)
        return self._safe(item)

    def approve_decision(self, decision_id: str, approved: bool = False) -> dict[str, Any]:
        decision = next((x for x in self.decisions if x["decision_id"] == decision_id), None)
        if not decision:
            return {"allowed": False, "reason": "decision_not_found"}
        gate = self.policy.evaluate("strategic_decision", approved=approved)
        if gate["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": gate}
        decision["status"] = "approved"
        self.lineage.record("decision.approved", "executive", "decision",
                            decision_id, "executive")
        return {"allowed": True, "decision_id": decision_id, "status": "approved"}

    def create_board_matter(self, title: str, source: str) -> dict[str, Any]:
        if not source.strip():
            return {"allowed": False, "reason": "source_required"}
        item = {"matter_id": f"BRD-{uuid.uuid4().hex[:10].upper()}",
                "title": title, "source": source, "status": "draft"}
        self.board_matters.append(item)
        return self._safe(item)

    def create_brief(self, title: str, content: str, confidence: float) -> dict[str, Any]:
        if not content.strip():
            return {"allowed": False, "reason": "content_required"}
        item = {"brief_id": f"BRF-{uuid.uuid4().hex[:10].upper()}",
                "title": title, "content": content, "confidence": confidence,
                "status": "draft"}
        self.briefs.append(item)
        return self._safe(item)

    def create_approval(self, action: str, approver: str) -> dict[str, Any]:
        item = {"approval_id": f"APR-{uuid.uuid4().hex[:10].upper()}",
                "action": action, "approver": approver, "status": "pending"}
        self.approvals.append(item)
        return self._safe(item)

    def portfolio_snapshot(self, data: dict[str, Any]) -> dict[str, Any]:
        snapshot = {"status": "current", "source_count": len(data),
                    "stale_data_flag": any(v is None for v in data.values()),
                    "data": data}
        return self._safe(snapshot)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "priorities": len(self.priorities),
                "decisions": len(self.decisions), "board_matters": len(self.board_matters),
                "briefs": len(self.briefs), "approvals": len(self.approvals),
                "credentials_exposed": False, "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ExecutiveFounder._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ExecutiveFounder._safe(v) for v in value]
        return value
