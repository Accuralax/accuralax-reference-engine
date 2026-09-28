from __future__ import annotations

from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

from .health import HealthEngine
from .repair import RepairPlanner
from .repair_circuit import RepairCircuitBreaker
from .repair_history import SQLiteRepairHistory


class RepairGraphState(TypedDict, total=False):
    health_report: dict[str, Any]
    plans: list[dict[str, Any]]
    approved: bool
    repair_status: str
    audit_events: int
    iterations: int


def build_repair_graph(max_iterations: int = 3):
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    def observe(state: RepairGraphState) -> RepairGraphState:
        report = state.get("health_report")
        if report is None:
            report = HealthEngine().run()
        return {"health_report": report, "iterations": state.get("iterations", 0) + 1}

    def plan(state: RepairGraphState) -> RepairGraphState:
        plans = RepairPlanner().plan(state["health_report"])
        return {"plans": [p.__dict__ for p in plans]}

    def gate(state: RepairGraphState) -> RepairGraphState:
        plans = state.get("plans", [])
        if not plans:
            return {"repair_status": "healthy"}
        if state.get("approved", False):
            return {"repair_status": "approved_for_verification"}
        return {"repair_status": "awaiting_approval"}

    def audit(state: RepairGraphState) -> RepairGraphState:
        history = SQLiteRepairHistory()
        for p in state.get("plans", []):
            history.record(p["repair_id"], "graph_planned", state.get("repair_status", "unknown"), {"risk": p["risk"]})
        return {"audit_events": len(history.list())}

    def route(state: RepairGraphState) -> str:
        if state.get("iterations", 0) >= max_iterations:
            return "end"
        return "end"

    graph = StateGraph(RepairGraphState)
    graph.add_node("observe", observe)
    graph.add_node("plan", plan)
    graph.add_node("gate", gate)
    graph.add_node("audit", audit)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "plan")
    graph.add_edge("plan", "gate")
    graph.add_edge("gate", "audit")
    graph.add_conditional_edges("audit", route, {"end": END})
    return graph.compile()


def run_repair_graph(health_report: dict[str, Any] | None = None, approved: bool = False) -> RepairGraphState:
    return build_repair_graph().invoke({"health_report": health_report} if health_report else {"approved": approved})
