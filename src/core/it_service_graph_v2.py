from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .it_operational_store import ITOperationalStore
from .it_incident_orchestration import ITIncidentOrchestrator


class PersistentITGraphState(TypedDict, total=False):
    request: str
    reference_id: str
    ticket_id: str
    asset_ids: list[str]
    action: str | None
    approved: bool
    status: str
    workstream: str | None
    selected_agent: str | None
    resumed: bool
    verification_status: str
    history: list[str]
    credentials_exposed: bool


def _history(state: PersistentITGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_persistent_it_graph(store: ITOperationalStore | None = None):
    operational_store = store or ITOperationalStore()
    orchestrator = ITIncidentOrchestrator()

    graph = StateGraph(PersistentITGraphState)

    def load(state: PersistentITGraphState) -> dict[str, Any]:
        ticket_id = state.get("ticket_id")
        reference_id = state.get("reference_id")
        if ticket_id:
            ticket = operational_store.get_ticket(ticket_id)
            if ticket:
                return {
                    "status": ticket["status"],
                    "reference_id": ticket["reference_id"],
                    "ticket_id": ticket["ticket_id"],
                    "workstream": None,
                    "resumed": True,
                    "history": _history(state, "load"),
                    "credentials_exposed": False,
                }
        if reference_id:
            # References are not duplicated; callers can continue with a known ticket_id.
            return {"status": "new_request", "resumed": False, "history": _history(state, "load"), "credentials_exposed": False}
        return {"status": "new_request", "resumed": False, "history": _history(state, "load"), "credentials_exposed": False}

    def open_or_resume(state: PersistentITGraphState) -> dict[str, Any]:
        if state.get("resumed"):
            ticket = operational_store.get_ticket(state["ticket_id"])
            return {
                "status": ticket["status"] if ticket else "ticket_not_found",
                "history": _history(state, "open_or_resume"),
            }
        try:
            work = orchestrator.open(
                state.get("reference_id", "CFS-IT-UNSET"),
                state.get("request", ""),
                asset_ids=state.get("asset_ids", []),
            )
        except ValueError as exc:
            return {"status": str(exc), "history": _history(state, "open_or_resume"), "credentials_exposed": False}
        operational_store.save_ticket(work.ticket)
        for asset_id in work.asset_ids:
            operational_store.link_ticket_asset(work.ticket.ticket_id, asset_id)
        return {
            "ticket_id": work.ticket.ticket_id,
            "status": work.status,
            "workstream": work.workstream,
            "selected_agent": work.assigned_agent,
            "history": _history(state, "open_or_resume"),
            "credentials_exposed": False,
        }

    def approval(state: PersistentITGraphState) -> dict[str, Any]:
        action = state.get("action")
        if not action or not state.get("ticket_id"):
            return {"status": state.get("status", "verification"), "history": _history(state, "approval")}
        result = orchestrator.authorize_action(
            state["ticket_id"], action, approved=bool(state.get("approved", False))
        )
        status = "action_authorized" if result["allowed"] else (
            "awaiting_approval" if result.get("requires_approval") else "action_denied"
        )
        ticket = operational_store.get_ticket(state["ticket_id"])
        if ticket:
            ticket["status"] = status
        return {"status": status, "history": _history(state, "approval")}

    def verify(state: PersistentITGraphState) -> dict[str, Any]:
        if state.get("status") in {"awaiting_approval", "action_denied", "ticket_not_found", "classification_required", "secret_request_blocked"}:
            return {"verification_status": "pending", "history": _history(state, "verify")}
        return {"verification_status": "pass", "status": "ready_for_resolution", "history": _history(state, "verify")}

    def audit(state: PersistentITGraphState) -> dict[str, Any]:
        return {"history": _history(state, "audit"), "credentials_exposed": False}

    def after_load(state: PersistentITGraphState) -> str:
        return "open_or_resume"

    def after_open(state: PersistentITGraphState) -> str:
        return "approval" if state.get("action") else "verify"

    def after_approval(state: PersistentITGraphState) -> str:
        return "verify" if state.get("status") == "action_authorized" else "audit"

    graph.add_node("load", load)
    graph.add_node("open_or_resume", open_or_resume)
    graph.add_node("approval", approval)
    graph.add_node("verify", verify)
    graph.add_node("audit", audit)
    graph.add_edge(START, "load")
    graph.add_conditional_edges("load", after_load, {"open_or_resume": "open_or_resume"})
    graph.add_conditional_edges("open_or_resume", after_open, {"approval": "approval", "verify": "verify"})
    graph.add_conditional_edges("approval", after_approval, {"verify": "verify", "audit": "audit"})
    graph.add_edge("verify", "audit")
    graph.add_edge("audit", END)
    return graph.compile()


def run_persistent_it_graph(
    request: str = "",
    *,
    reference_id: str | None = None,
    ticket_id: str | None = None,
    asset_ids: list[str] | None = None,
    action: str | None = None,
    approved: bool = False,
    store: ITOperationalStore | None = None,
) -> PersistentITGraphState:
    return build_persistent_it_graph(store).invoke({
        "request": request,
        "reference_id": reference_id,
        "ticket_id": ticket_id,
        "asset_ids": asset_ids or [],
        "action": action,
        "approved": approved,
        "history": [],
    })
