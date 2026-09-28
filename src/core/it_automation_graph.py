from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .it_automation_supervisor import ITAutomationSupervisor
from .it_event_bus import ITEvent


class ITAutomationGraphState(TypedDict, total=False):
    event: ITEvent
    status: str
    attempts: int
    decisions: list[dict[str, Any]]
    reason: str | None
    cycle_count: int
    max_cycles: int
    history: list[str]
    terminal: bool
    approval_required: bool
    credentials_exposed: bool


def _history(state: ITAutomationGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_it_automation_graph(supervisor: ITAutomationSupervisor | None = None, *, max_cycles: int = 3):
    automation_supervisor = supervisor or ITAutomationSupervisor()
    graph = StateGraph(ITAutomationGraphState)

    def observe(state: ITAutomationGraphState) -> dict[str, Any]:
        return {
            "cycle_count": state.get("cycle_count", 0),
            "max_cycles": max_cycles,
            "status": "observed",
            "history": _history(state, "observe"),
            "credentials_exposed": False,
        }

    def gate(state: ITAutomationGraphState) -> dict[str, Any]:
        event = state.get("event")
        if not event:
            return {"status": "terminal_failure", "terminal": True, "reason": "event_required", "history": _history(state, "gate")}
        if state.get("cycle_count", 0) >= max_cycles:
            return {"status": "cycle_limit", "terminal": True, "reason": "max_cycles_reached", "history": _history(state, "gate")}
        return {"status": "ready", "history": _history(state, "gate")}

    def execute(state: ITAutomationGraphState) -> dict[str, Any]:
        event = state["event"]
        run = automation_supervisor.handle(event)
        return {
            "status": run.status,
            "attempts": run.attempts,
            "decisions": [
                {"rule_id": d.rule_id, "allowed": d.allowed, "action": d.action, "reason": d.reason, "requires_approval": d.requires_approval}
                for d in run.decisions
            ],
            "reason": run.reason,
            "approval_required": run.status == "awaiting_approval",
            "history": _history(state, "execute"),
            "credentials_exposed": False,
        }

    def terminal(state: ITAutomationGraphState) -> dict[str, Any]:
        return {"terminal": True, "history": _history(state, "terminal"), "credentials_exposed": False}

    def after_gate(state: ITAutomationGraphState) -> str:
        return "terminal" if state.get("terminal") else "execute"

    graph.add_node("observe", observe)
    graph.add_node("gate", gate)
    graph.add_node("execute", execute)
    graph.add_node("terminal", terminal)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "gate")
    graph.add_conditional_edges("gate", after_gate, {"execute": "execute", "terminal": "terminal"})
    graph.add_edge("execute", "terminal")
    graph.add_edge("terminal", END)
    return graph.compile()


def run_it_automation_graph(event: ITEvent, *, supervisor: ITAutomationSupervisor | None = None, max_cycles: int = 3) -> ITAutomationGraphState:
    return build_it_automation_graph(supervisor, max_cycles=max_cycles).invoke({
        "event": event,
        "history": [],
        "cycle_count": 0,
        "max_cycles": max_cycles,
        "credentials_exposed": False,
    })
