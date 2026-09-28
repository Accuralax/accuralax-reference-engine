from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .cybersecurity_runtime import CybersecurityRuntime
from .supervisor import AgentSupervisor


class SecurityGraphState(TypedDict, total=False):
    request: str
    authorized_scope: bool
    live_red_testing: bool
    approved: bool
    domain: str | None
    reference_id: str
    selected_agent: str
    authorization: dict[str, Any]
    knowledge: list[dict[str, Any]]
    finding: dict[str, Any]
    risk: str
    remediation: dict[str, Any]
    product: dict[str, Any] | None
    status: str
    history: list[str]


def _history(state: SecurityGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_security_graph():
    runtime = CybersecurityRuntime()
    supervisor = AgentSupervisor()
    graph = StateGraph(SecurityGraphState)

    def scope(state: SecurityGraphState) -> dict[str, Any]:
        session = runtime.start(authorized_scope=bool(state.get("authorized_scope", False)))
        return {"reference_id": session.reference_id, "status": session.status, "history": _history(state, "scope")}

    def agent_authorization(state: SecurityGraphState) -> dict[str, Any]:
        decision = supervisor.authorize_delegation("supervisor", "cybersecurity_triage_agent", count=0)
        if not decision.allowed:
            return {"status": "blocked_authorization", "history": _history(state, "agent_authorization")}
        return {
            "selected_agent": decision.child_agent,
            "authorization": supervisor.authorization_snapshot(decision.child_agent),
            "status": "authorized",
            "history": _history(state, "agent_authorization"),
        }

    def intelligence(state: SecurityGraphState) -> dict[str, Any]:
        session = runtime.start(authorized_scope=True)
        session.reference_id = state["reference_id"]
        hits = runtime.retrieve_security_knowledge(session, state.get("request", ""), domain=state.get("domain"))
        return {"knowledge": runtime.rag.provenance(hits), "status": "intelligence_ready" if hits else "knowledge_gap", "history": _history(state, "security_rag")}

    def threat_model(state: SecurityGraphState) -> dict[str, Any]:
        query = state.get("request", "").lower()
        category = state.get("domain")
        if not category:
            for candidate in ("identity", "endpoint", "web", "data", "incident"):
                if candidate in query:
                    category = candidate
                    break
        finding = {"category": category or "unknown", "summary": "Bounded threat/control hypothesis derived from the authorized request.", "evidence": list(state.get("knowledge", []))}
        return {"finding": finding, "status": "threat_model_ready" if category else "classification_required", "history": _history(state, "threat_model")}

    def red_validation(state: SecurityGraphState) -> dict[str, Any]:
        if state.get("status") == "classification_required":
            return {"status": "blocked_classification", "history": _history(state, "red_validation")}
        session = runtime.start(authorized_scope=True)
        session.reference_id = state["reference_id"]
        runtime.run_validation(session, state["finding"], live_red_testing=bool(state.get("live_red_testing", False)), approved=bool(state.get("approved", False)))
        return {"status": "awaiting_approval" if session.status == "awaiting_approval" else "red_validated", "history": _history(state, "red_validation")}

    def blue_defense(state: SecurityGraphState) -> dict[str, Any]:
        return {"status": "blue_defense_ready", "history": _history(state, "blue_defense")} if state.get("status") == "red_validated" else {"status": state.get("status", "blocked"), "history": _history(state, "blue_defense")}

    def purple_verify(state: SecurityGraphState) -> dict[str, Any]:
        return {"status": "purple_verified", "history": _history(state, "purple_verify")} if state.get("status") == "blue_defense_ready" else {"status": state.get("status", "blocked"), "history": _history(state, "purple_verify")}

    def risk_assessment(state: SecurityGraphState) -> dict[str, Any]:
        evidence_count = len(state.get("knowledge", []))
        risk = "high" if state.get("finding", {}).get("category") == "incident" else ("medium" if evidence_count else "unknown")
        return {"risk": risk, "status": "risk_assessed", "history": _history(state, "risk_assessment")}

    def remediation(state: SecurityGraphState) -> dict[str, Any]:
        risk = state.get("risk", "unknown")
        if risk == "unknown":
            return {"status": "remediation_review_required", "history": _history(state, "remediation")}
        return {"remediation": {"mode": "proposal_only", "risk": risk, "actions": ["review_control_gap", "apply_approved_hardening", "retest", "audit"], "requires_human_approval": True}, "status": "remediation_proposed", "history": _history(state, "remediation")}

    def product_opportunity(state: SecurityGraphState) -> dict[str, Any]:
        if state.get("status") != "remediation_proposed":
            return {"product": None, "history": _history(state, "product_opportunity")}
        session = runtime.start(authorized_scope=True)
        session.finding = dict(state.get("finding", {}))
        product = runtime.product_opportunity(session)
        return {"product": product.__dict__ if product else None, "status": "product_opportunity_identified" if product else "cycle_complete", "history": _history(state, "product_opportunity")}

    def audit(state: SecurityGraphState) -> dict[str, Any]:
        return {"status": state.get("status", "complete"), "history": _history(state, "audit")}

    def route_scope(state: SecurityGraphState) -> str:
        return "agent_authorization" if state.get("status") == "ready" else "audit"

    def route_authorization(state: SecurityGraphState) -> str:
        return "intelligence" if state.get("status") == "authorized" else "audit"

    def route_red(state: SecurityGraphState) -> str:
        return "blue" if state.get("status") == "red_validated" else "audit"

    def route_blue(state: SecurityGraphState) -> str:
        return "purple" if state.get("status") == "blue_defense_ready" else "audit"

    def route_purple(state: SecurityGraphState) -> str:
        return "risk" if state.get("status") == "purple_verified" else "audit"

    for name, fn in [
        ("scope", scope), ("agent_authorization", agent_authorization), ("intelligence", intelligence), ("threat_model", threat_model),
        ("red_validation", red_validation), ("blue_defense", blue_defense),
        ("purple_verify", purple_verify), ("risk_assessment", risk_assessment),
        ("remediation", remediation), ("product_opportunity", product_opportunity), ("audit", audit)
    ]:
        graph.add_node(name, fn)

    graph.add_edge(START, "scope")
    graph.add_conditional_edges("scope", route_scope, {"agent_authorization": "agent_authorization", "audit": "audit"})
    graph.add_conditional_edges("agent_authorization", route_authorization, {"intelligence": "intelligence", "audit": "audit"})
    graph.add_edge("intelligence", "threat_model")
    graph.add_edge("threat_model", "red_validation")
    graph.add_conditional_edges("red_validation", route_red, {"blue": "blue_defense", "audit": "audit"})
    graph.add_conditional_edges("blue_defense", route_blue, {"purple": "purple_verify", "audit": "audit"})
    graph.add_conditional_edges("purple_verify", route_purple, {"risk": "risk_assessment", "audit": "audit"})
    graph.add_edge("risk_assessment", "remediation")
    graph.add_edge("remediation", "product_opportunity")
    graph.add_edge("product_opportunity", "audit")
    graph.add_edge("audit", END)
    return graph.compile()


def run_security_graph(request: str, *, authorized_scope: bool = False, domain: str | None = None, live_red_testing: bool = False, approved: bool = False) -> SecurityGraphState:
    return build_security_graph().invoke({"request": request, "authorized_scope": authorized_scope, "domain": domain, "live_red_testing": live_red_testing, "approved": approved, "history": []})
