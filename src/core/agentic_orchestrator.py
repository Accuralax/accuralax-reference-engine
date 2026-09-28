from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import uuid
import yaml

from .agent_permissions import AgentPermissionRegistry
from .enterprise_control_plane import EnterpriseControlPlane
from .governance_engine import GovernanceEngine
from .langgraph_checkpoint import LangGraphCheckpointStore
from .agentic_trace import AgenticTrace


@dataclass
class OrchestrationState:
    reference_id: str
    request: str
    current_agent: str = "supervisor"
    delegated: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    status: str = "initialized"
    approval_required: bool = False
    error: str | None = None


class AgenticOrchestrator:
    """Governed hierarchical execution fabric for supervisors, specialists and sub-agents."""

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "agentic_orchestration.yaml").read_text(encoding="utf-8")) or {}
        self.permissions = AgentPermissionRegistry()
        self.control = EnterpriseControlPlane()
        self.governance = GovernanceEngine()
        self.checkpoints = LangGraphCheckpointStore()

    def start(self, request: str, reference_id: str | None = None) -> OrchestrationState:
        ref = reference_id or f"CFS-ORCH-{uuid.uuid4().hex[:10].upper()}"
        state = OrchestrationState(reference_id=ref, request=request)
        state.steps.append("supervisor")
        state.status = "routing"
        self.checkpoints.save(ref, "supervisor", self._dict(state))
        return state

    def delegate(self, state: OrchestrationState, target_agent: str, scope: str) -> OrchestrationState:
        if len(state.delegated) >= self.config["orchestration"]["max_delegations"]:
            state.status = "terminated"
            state.error = "delegation_limit_reached"
            return state
        policy = self.permissions.get(target_agent)
        allowed = bool(policy and scope and ("knowledge_lookup" in policy.allowed_skills or "service_triage" in policy.allowed_skills or "cybersecurity_triage" in policy.allowed_skills or "proposal_scoping" in policy.allowed_skills))
        if not allowed:
            state.status = "escalated"
            state.error = "delegation_not_authorized"
            return state
        if target_agent in state.delegated:
            state.status = "terminated"
            state.error = "delegation_cycle_detected"
            return state
        state.delegated.append(target_agent)
        state.current_agent = target_agent
        state.steps.append(target_agent)
        state.status = "executing"
        self.checkpoints.save(state.reference_id, target_agent, self._dict(state))
        return state

    def gate(self, state: OrchestrationState, action: str, *,
             high_risk: bool = False, destructive: bool = False,
             external_side_effect: bool = False, approved: bool = False,
             policy_check_passed: bool = False) -> OrchestrationState:
        control = self.control.authorize(action, high_risk=high_risk, destructive=destructive,
                                         external_side_effect=external_side_effect, approved=approved)
        policy = self.governance.evaluate(
            action,
            context={"policy_check_passed": policy_check_passed},
            approved=approved,
            human_reviewed=approved,
        )
        if not control["allowed"] or policy["outcome"] not in {"allowed", "approved"}:
            state.approval_required = True
            state.status = "awaiting_approval" if "approval" in policy["outcome"] or not control["allowed"] else "awaiting_policy"
        else:
            state.status = "verified"
        self.checkpoints.save(state.reference_id, "governance_gate", self._dict(state))
        return state

    def complete(self, state: OrchestrationState, *, verified: bool = True) -> dict[str, Any]:
        state.status = "completed" if verified and not state.approval_required else state.status
        trace = AgenticTrace(state.reference_id)
        for step in state.steps:
            trace.record(step, "completed" if state.status == "completed" else state.status)
        trace.record("orchestrator", state.status, delegated=len(state.delegated),
                     approval_required=state.approval_required, credentials_exposed=False)
        self.checkpoints.save(state.reference_id, "complete", self._dict(state))
        return {
            "reference_id": state.reference_id,
            "status": state.status,
            "current_agent": state.current_agent,
            "delegated": state.delegated,
            "steps": state.steps,
            "approval_required": state.approval_required,
            "trace": trace.summary(),
            "credentials_exposed": False,
        }

    @staticmethod
    def _dict(state: OrchestrationState) -> dict[str, Any]:
        return {
            "reference_id": state.reference_id, "request": state.request,
            "current_agent": state.current_agent, "delegated": state.delegated,
            "steps": state.steps, "status": state.status,
            "approval_required": state.approval_required, "error": state.error,
            "credentials_exposed": False,
        }

    def resume(self, reference_id: str) -> dict[str, Any]:
        checkpoint = self.checkpoints.latest(reference_id)
        return {"resumable": checkpoint is not None,
                "checkpoint": checkpoint.state if checkpoint else None,
                "node": checkpoint.node if checkpoint else None,
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "backbone": "langgraph",
                "bounded": True, "cycle_detection": True,
                "checkpoint_required": True, "trace_required": True,
                "credentials_exposed": False}
