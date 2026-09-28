from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .service_router import ServiceRouter


class AgentGraphState(TypedDict, total=False):
    request: str
    reference_id: str
    safety_status: str
    service_id: str | None
    service_name: str | None
    active_agent: str
    active_skills: list[str]
    verification_status: str
    status: str
    history: list[str]
    error: str | None


def _append(state: AgentGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_langgraph():
    """Build the first real LangGraph runtime over the existing deterministic controls."""
    graph = StateGraph(AgentGraphState)

    def safety_guard(state: AgentGraphState) -> dict[str, Any]:
        request = state.get("request", "").lower()
        forbidden = ("password", "api key", "apikey", "authentication token", "card number")
        blocked = any(item in request for item in forbidden)
        return {
            "safety_status": "blocked_sensitive_request" if blocked else "pass",
            "status": "blocked" if blocked else "intake",
            "history": _append(state, "safety_guard"),
        }

    def intake(state: AgentGraphState) -> dict[str, Any]:
        return {"active_agent": "intake_agent", "status": "routing", "history": _append(state, "intake")}

    def service_router(state: AgentGraphState) -> dict[str, Any]:
        match = ServiceRouter().route(state.get("request", ""))
        if not match or not match.service_id:
            return {
                "service_id": None,
                "service_name": None,
                "active_agent": "service_triage_agent",
                "status": "clarification_required",
                "history": _append(state, "service_router"),
            }
        return {
            "service_id": match.service_id,
            "service_name": match.service_name,
            "active_agent": "supervisor",
            "status": "verification",
            "history": _append(state, "service_router"),
        }

    def specialist_selector(state: AgentGraphState) -> dict[str, Any]:
        service = state.get("service_id")
        mapping = {
            "cybersecurity": ("cybersecurity_triage_agent", ["safety_guard", "intake", "service_triage", "knowledge_lookup", "cybersecurity_triage"]),
            "ai_automation": ("ai_automation_agent", ["safety_guard", "intake", "service_triage", "knowledge_lookup", "proposal_scoping"]),
            "website": ("digital_agent", ["safety_guard", "intake", "service_triage", "knowledge_lookup", "proposal_scoping"]),
            "software_app": ("digital_agent", ["safety_guard", "intake", "service_triage", "knowledge_lookup", "proposal_scoping"]),
        }
        agent, skills = mapping.get(service, ("business_operations_agent", ["safety_guard", "intake", "service_triage", "knowledge_lookup"]))
        return {"active_agent": agent, "active_skills": skills, "status": "verification", "history": _append(state, "specialist_selector")}

    def verifier(state: AgentGraphState) -> dict[str, Any]:
        if state.get("status") in {"blocked", "clarification_required"}:
            return {"verification_status": "not_required", "history": _append(state, "verifier")}
        return {"verification_status": "pass", "status": "ready_for_response", "history": _append(state, "verifier")}

    def safety_route(state: AgentGraphState) -> str:
        return "end" if state.get("safety_status") == "blocked_sensitive_request" else "intake"

    def route_after_intake(state: AgentGraphState) -> str:
        return "end" if state.get("status") == "blocked" else "service_router"

    def route_after_router(state: AgentGraphState) -> str:
        return "end" if state.get("status") == "clarification_required" else "specialist_selector"

    graph.add_node("safety_guard", safety_guard)
    graph.add_node("intake", intake)
    graph.add_node("service_router", service_router)
    graph.add_node("specialist_selector", specialist_selector)
    graph.add_node("verifier", verifier)
    graph.add_edge(START, "safety_guard")
    graph.add_conditional_edges("safety_guard", safety_route, {"intake": "intake", "end": END})
    graph.add_conditional_edges("intake", route_after_intake, {"service_router": "service_router", "end": END})
    graph.add_conditional_edges("service_router", route_after_router, {"specialist_selector": "specialist_selector", "end": END})
    graph.add_edge("specialist_selector", "verifier")
    graph.add_edge("verifier", END)
    return graph.compile()


def run_langgraph(request: str) -> AgentGraphState:
    return build_langgraph().invoke({"request": request, "history": []})
