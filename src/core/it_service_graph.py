from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .it_service_runtime import ITServiceRuntime


class ITGraphState(TypedDict, total=False):
    request: str
    reference_id: str
    workstream: str | None
    selected_agent: str | None
    diagnosis: str
    action: str | None
    approved: bool
    verification_status: str
    status: str
    history: list[str]
    credentials_exposed: bool
    approvals_required: list[str]


def _history(state: ITGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_it_service_graph():
    runtime = ITServiceRuntime()
    graph = StateGraph(ITGraphState)

    def intake(state: ITGraphState) -> dict[str, Any]:
        return {"status": "intake", "history": _history(state, "intake")}

    def triage(state: ITGraphState) -> dict[str, Any]:
        session = runtime.start(state.get("request", ""))
        return {"reference_id": session.reference_id, "workstream": session.workstreams[0] if session.workstreams else None, "selected_agent": next(iter(session.selected_agents.values()), None), "status": session.status, "credentials_exposed": False, "history": _history(state, "triage")}

    def diagnose(state: ITGraphState) -> dict[str, Any]:
        if state.get("status") != "triaged":
            return {"status": state.get("status", "blocked"), "history": _history(state, "diagnose")}
        return {"diagnosis": "Bounded diagnostic stage complete; no system change performed.", "status": "diagnosed", "history": _history(state, "diagnose")}

    def approval_gate(state: ITGraphState) -> dict[str, Any]:
        action = state.get("action")
        if not action:
            return {"status": "verification", "history": _history(state, "approval_gate")}
        session = runtime.start(state.get("request", ""))
        result = runtime.authorize_action(session, action, approved=bool(state.get("approved", False)))
        if result["allowed"]:
            return {"status": "action_authorized", "history": _history(state, "approval_gate")}
        return {"status": "awaiting_approval" if result.get("requires_approval") else "action_denied", "approvals_required": [action] if result.get("requires_approval") else [], "history": _history(state, "approval_gate")}

    def verify(state: ITGraphState) -> dict[str, Any]:
        if state.get("status") in {"action_denied", "awaiting_approval"}:
            return {"verification_status": "pending", "history": _history(state, "verify")}
        return {"verification_status": "pass", "status": "ready_for_resolution", "history": _history(state, "verify")}

    def audit(state: ITGraphState) -> dict[str, Any]:
        return {"status": state.get("status", "complete"), "history": _history(state, "audit"), "credentials_exposed": False}

    def after_triage(state: ITGraphState) -> str:
        return "diagnose" if state.get("status") == "triaged" else "audit"

    def after_diagnose(state: ITGraphState) -> str:
        return "approval_gate" if state.get("action") else "verify"

    def after_approval(state: ITGraphState) -> str:
        return "verify" if state.get("status") == "action_authorized" else "audit"

    graph.add_node("intake", intake)
    graph.add_node("triage", triage)
    graph.add_node("diagnose", diagnose)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("verify", verify)
    graph.add_node("audit", audit)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "triage")
    graph.add_conditional_edges("triage", after_triage, {"diagnose": "diagnose", "audit": "audit"})
    graph.add_conditional_edges("diagnose", after_diagnose, {"approval_gate": "approval_gate", "verify": "verify"})
    graph.add_conditional_edges("approval_gate", after_approval, {"verify": "verify", "audit": "audit"})
    graph.add_edge("verify", "audit")
    graph.add_edge("audit", END)
    return graph.compile()


def run_it_service_graph(request: str, *, action: str | None = None, approved: bool = False) -> ITGraphState:
    return build_it_service_graph().invoke({"request": request, "action": action, "approved": approved, "history": []})
