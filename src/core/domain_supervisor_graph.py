from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .domain_supervisors import DomainSupervisorRegistry


class DomainSupervisorGraphState(TypedDict, total=False):
    domain: str
    specialist: str | None
    action: str | None
    approved: bool
    delegation_count: int
    max_delegations: int
    status: str
    reason: str
    verification_status: str
    history: list[str]
    terminal: bool
    credentials_exposed: bool


def _history(state: DomainSupervisorGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_domain_supervisor_graph(*, max_delegations: int = 6):
    registry = DomainSupervisorRegistry()
    graph = StateGraph(DomainSupervisorGraphState)

    def intake(state: DomainSupervisorGraphState) -> dict[str, Any]:
        return {"status": "intake", "history": _history(state, "intake"), "credentials_exposed": False}

    def domain_gate(state: DomainSupervisorGraphState) -> dict[str, Any]:
        supervisor = registry.get(state.get("domain", ""))
        if supervisor is None:
            return {"status": "unknown_domain", "reason": "unknown_domain", "terminal": True, "history": _history(state, "domain_gate")}
        return {
            "status": "domain_valid",
            "max_delegations": min(max_delegations, supervisor.config["max_delegations"]),
            "history": _history(state, "domain_gate"),
            "credentials_exposed": False,
        }

    def delegation(state: DomainSupervisorGraphState) -> dict[str, Any]:
        supervisor = registry.get(state.get("domain", ""))
        if supervisor is None:
            return {"status": "unknown_domain", "terminal": True, "history": _history(state, "delegation")}
        count = state.get("delegation_count", 0) + 1
        graph_limit = state.get("max_delegations", supervisor.config["max_delegations"])
        if count > graph_limit:
            return {"delegation_count": count, "status": "delegation_limit", "reason": "max_delegations_reached", "terminal": True, "history": _history(state, "delegation"), "credentials_exposed": False}
        decision = supervisor.delegate(
            state.get("specialist"),
            action=state.get("action"),
            approved=bool(state.get("approved", False)),
            delegation_count=count - 1,
        )
        return {
            "delegation_count": count,
            "status": "delegated" if decision.allowed else ("awaiting_approval" if decision.requires_approval else decision.reason),
            "reason": decision.reason,
            "terminal": not decision.allowed and not decision.requires_approval and decision.reason != "human_approval_required",
            "history": _history(state, "delegation"),
            "credentials_exposed": False,
        }

    def verify(state: DomainSupervisorGraphState) -> dict[str, Any]:
        status = state.get("status")
        if status == "delegated":
            return {"verification_status": "pass", "status": "ready_for_specialist", "history": _history(state, "verify")}
        return {"verification_status": "pending", "history": _history(state, "verify")}

    def approval_review(state: DomainSupervisorGraphState) -> dict[str, Any]:
        return {"verification_status": "pending", "terminal": False, "history": _history(state, "approval_review"), "credentials_exposed": False}

    def terminal(state: DomainSupervisorGraphState) -> dict[str, Any]:
        return {"terminal": True, "history": _history(state, "terminal"), "credentials_exposed": False}

    def after_gate(state: DomainSupervisorGraphState) -> str:
        return "terminal" if state.get("terminal") else "delegation"

    def after_delegation(state: DomainSupervisorGraphState) -> str:
        if state.get("status") == "delegated":
            return "verify"
        if state.get("status") == "awaiting_approval":
            return "approval_review"
        return "terminal"

    graph.add_node("intake", intake)
    graph.add_node("domain_gate", domain_gate)
    graph.add_node("delegation", delegation)
    graph.add_node("verify", verify)
    graph.add_node("approval_review", approval_review)
    graph.add_node("terminal", terminal)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "domain_gate")
    graph.add_conditional_edges("domain_gate", after_gate, {"delegation": "delegation", "terminal": "terminal"})
    graph.add_conditional_edges("delegation", after_delegation, {"verify": "verify", "approval_review": "approval_review", "terminal": "terminal"})
    graph.add_edge("verify", "terminal")
    graph.add_edge("approval_review", END)
    graph.add_edge("terminal", END)
    return graph.compile()


def run_domain_supervisor_graph(
    domain: str,
    specialist: str | None,
    *,
    action: str | None = None,
    approved: bool = False,
    max_delegations: int = 6,
) -> DomainSupervisorGraphState:
    return build_domain_supervisor_graph(max_delegations=max_delegations).invoke({
        "domain": domain,
        "specialist": specialist,
        "action": action,
        "approved": approved,
        "delegation_count": 0,
        "history": [],
        "credentials_exposed": False,
    })
