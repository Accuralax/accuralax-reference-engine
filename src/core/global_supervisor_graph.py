from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .global_supervisor import GlobalSupervisor
from .domain_supervisors import DomainSupervisor
from .domain_supervisor_graph import run_domain_supervisor_graph


class GlobalSupervisorGraphState(TypedDict, total=False):
    request: str
    domain: str
    specialist: str | None
    status: str
    reason: str
    action: str | None
    approved: bool
    delegation_count: int
    max_delegations: int
    domain_delegation_count: int
    verification_status: str
    domain_supervisor_status: str
    domain_supervisor_reason: str
    domain_supervisor_history: list[str]
    history: list[str]
    terminal: bool
    credentials_exposed: bool


def _history(state: GlobalSupervisorGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_global_supervisor_graph(*, max_delegations: int = 5):
    supervisor = GlobalSupervisor()
    graph = StateGraph(GlobalSupervisorGraphState)

    def intake(state: GlobalSupervisorGraphState) -> dict[str, Any]:
        return {"status": "intake", "history": _history(state, "intake"), "credentials_exposed": False}

    def route(state: GlobalSupervisorGraphState) -> dict[str, Any]:
        result = supervisor.route(state.get("request", ""))
        return {
            "domain": result.domain,
            "specialist": result.specialist,
            "status": "routed" if result.allowed else result.reason,
            "reason": result.reason,
            "history": _history(state, "route"),
            "credentials_exposed": False,
        }

    def delegation_gate(state: GlobalSupervisorGraphState) -> dict[str, Any]:
        count = state.get("delegation_count", 0) + 1
        if count > max_delegations:
            return {
                "delegation_count": count,
                "status": "delegation_limit",
                "reason": "max_delegations_reached",
                "terminal": True,
                "history": _history(state, "delegation_gate"),
                "credentials_exposed": False,
            }
        if not state.get("specialist"):
            return {
                "delegation_count": count,
                "status": "no_specialist",
                "terminal": True,
                "history": _history(state, "delegation_gate"),
                "credentials_exposed": False,
            }
        return {
            "delegation_count": count,
            "status": "delegation_authorized",
            "history": _history(state, "delegation_gate"),
            "credentials_exposed": False,
        }

    def domain_supervisor(state: GlobalSupervisorGraphState) -> dict[str, Any]:
        domain_state = run_domain_supervisor_graph(
            state.get("domain", ""),
            state.get("specialist"),
            action=state.get("action"),
            approved=bool(state.get("approved", False)),
            max_delegations=max(1, max_delegations - state.get("delegation_count", 0)),
        )
        status = domain_state.get("status", "unknown")
        waiting = status == "awaiting_approval"
        terminal = bool(domain_state.get("terminal", False)) if not waiting else False
        return {
            "domain_supervisor_status": status,
            "domain_supervisor_reason": domain_state.get("reason", ""),
            "domain_supervisor_history": domain_state.get("history", []),
            "domain_delegation_count": domain_state.get("delegation_count", 0),
            "status": "awaiting_approval" if waiting else (
                "ready_for_specialist" if status == "ready_for_specialist" else status
            ),
            "reason": domain_state.get("reason", state.get("reason", "")),
            "verification_status": domain_state.get("verification_status", "pending"),
            "terminal": terminal,
            "history": _history(state, "domain_supervisor"),
            "credentials_exposed": False,
        }

    def terminal(state: GlobalSupervisorGraphState) -> dict[str, Any]:
        return {"terminal": True, "history": _history(state, "terminal"), "credentials_exposed": False}

    def after_route(state: GlobalSupervisorGraphState) -> str:
        return "terminal" if state.get("status") == "clarification_required" else "delegation_gate"

    def after_delegation(state: GlobalSupervisorGraphState) -> str:
        return "terminal" if state.get("terminal") else "domain_supervisor"

    def after_domain(state: GlobalSupervisorGraphState) -> str:
        return "terminal" if state.get("terminal") else END

    graph.add_node("intake", intake)
    graph.add_node("route", route)
    graph.add_node("delegation_gate", delegation_gate)
    graph.add_node("domain_supervisor", domain_supervisor)
    graph.add_node("terminal", terminal)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "route")
    graph.add_conditional_edges("route", after_route, {"delegation_gate": "delegation_gate", "terminal": "terminal"})
    graph.add_conditional_edges("delegation_gate", after_delegation, {"domain_supervisor": "domain_supervisor", "terminal": "terminal"})
    graph.add_conditional_edges("domain_supervisor", after_domain, {"terminal": "terminal", END: END})
    graph.add_edge("terminal", END)
    return graph.compile()


def run_global_supervisor_graph(
    request: str,
    *,
    action: str | None = None,
    approved: bool = False,
    max_delegations: int = 5,
) -> GlobalSupervisorGraphState:
    return build_global_supervisor_graph(max_delegations=max_delegations).invoke({
        "request": request,
        "action": action,
        "approved": approved,
        "delegation_count": 0,
        "history": [],
        "credentials_exposed": False,
    })
