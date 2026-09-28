from .agent_knowledge_runtime import AgentKnowledgeRuntime
from .agentic_trace import AgenticTrace
from .enterprise_control_plane import EnterpriseControlPlane
from .langgraph_runtime import run_langgraph
from .runtime_contract import RuntimeExecutionContract
from .enterprise_state import EnterpriseState
from .tenant_access import AccessContext, TenantAccess


class AgenticWorkspace:
    """Unified runtime boundary for routing, knowledge, policy and trace."""

    def __init__(self) -> None:
        self.knowledge = AgentKnowledgeRuntime()
        self.control_plane = EnterpriseControlPlane()
        self.state = EnterpriseState()
        self.access = TenantAccess()

    def run(self, request: str, *, tenant_id: str = "default",
            workspace_id: str = "default", actor_id: str = "system",
            channel: str = "internal", role: str = "agent", trust: str = "verified") -> dict:
        access = self.access.authorize(AccessContext(tenant_id=tenant_id, workspace_id=workspace_id, actor_id=actor_id, role=role, trust=trust), "execute_bounded", tenant_id, workspace_id)
        if not access["allowed"]:
            return {"status":"blocked", "reason":"access_denied", "authorization":access, "credentials_exposed":False}
        contract = RuntimeExecutionContract(
            tenant_id=tenant_id, workspace_id=workspace_id,
            actor_id=actor_id, channel=channel, request=request,
            status="running",
        )
        state = run_langgraph(request)
        ref = state.get("reference_id") or contract.reference_id
        contract.reference_id = ref
        contract.safety_status = state.get("safety_status", "pending")
        contract.status = state.get("status", "failed")
        contract.domain = state.get("service_id")
        contract.agent = state.get("active_agent")
        contract.skill = (state.get("active_skills") or [None])[0]
        contract.verification_status = state.get("verification_status")
        contract.context["history"] = state.get("history", [])
        if contract.status == "ready_for_response":
            contract.status = "completed"
        if contract.safety_status == "blocked_sensitive_request":
            contract.status = "blocked"

        decision = self.control_plane.authorize(
            "agent.run",
            high_risk=contract.risk_level in {"high", "critical"},
            external_side_effect=False,
            approved=False,
        )
        contract.add_policy_decision(decision)
        if not decision["allowed"]:
            contract.status = "awaiting_approval"
            contract.approval_state = "pending"

        trace = AgenticTrace(ref)
        history = state.get("history", ["supervisor"])
        active_agent = state.get("active_agent") or history[-1]
        context = self.knowledge.context(active_agent, request)
        if contract.status == "completed":
            self.knowledge.learn_experience(
                active_agent, request, state.get("verification_status", "completed"), ref
            )
        trace.record(
            history[-1], state.get("status", "unknown"),
            active_agent=active_agent, service_id=state.get("service_id"),
            verification_status=state.get("verification_status"),
            memory_count=len(context["memory"]),
            knowledge_count=len(context["knowledge"]),
            skill_count=len(context["skills"]),
            credentials_exposed=False,
        )
        contract.validate()
        self.state.save_execution(contract.to_dict())
        self.state.append_audit(contract.reference_id, history[-1], contract.status, {
            "agent": active_agent, "service_id": state.get("service_id"),
            "verification_status": state.get("verification_status")
        })
        return {
            "reference_id": contract.reference_id,
            "request_id": contract.request_id,
            "trace_id": contract.trace_id,
            "status": contract.status,
            "safety_status": contract.safety_status,
            "approval_state": contract.approval_state,
            "policy_decisions": contract.policy_decisions,
            "service_id": state.get("service_id"),
            "service_name": state.get("service_name"),
            "active_agent": active_agent,
            "active_skills": state.get("active_skills", context["skills"]),
            "brain": {
                "domains": context["agent"]["domains"],
                "memory_count": len(context["memory"]),
                "memories": context["memory"],
                "knowledge": context["knowledge"],
                "skills": context["skills"],
                "credentials_exposed": False,
            },
            "verification_status": state.get("verification_status"),
            "history": history,
            "trace": trace.summary(),
            "credentials_exposed": False,
            "runtime_contract": contract.to_dict(),
        }
