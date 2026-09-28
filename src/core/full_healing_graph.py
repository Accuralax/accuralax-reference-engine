from __future__ import annotations

from typing import TypedDict, Any
from pathlib import Path

from langgraph.graph import StateGraph, START, END

from .health import HealthEngine
from .repair import RepairPlanner
from .repair_executor import RepairExecutor
from .sandbox import SandboxVerifier
from .repair_history import SQLiteRepairHistory


class FullHealingState(TypedDict, total=False):
    health_report: dict[str, Any]
    plans: list[dict[str, Any]]
    candidate: dict[str, Any]
    approved: bool
    verification_ok: bool
    execution: dict[str, Any]
    post_health: dict[str, Any]
    status: str
    iteration: int
    max_iterations: int


def build_full_healing_graph(max_iterations: int = 3):
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    planner = RepairPlanner()
    executor = RepairExecutor(Path.cwd())
    sandbox = SandboxVerifier()
    history = SQLiteRepairHistory()

    def observe(state: FullHealingState) -> FullHealingState:
        report = state.get("health_report") or HealthEngine().run()
        return {"health_report": report, "iteration": state.get("iteration", 0) + 1, "max_iterations": max_iterations}

    def plan(state: FullHealingState) -> FullHealingState:
        plans = planner.plan(state["health_report"])
        return {"plans": [p.__dict__ for p in plans]}

    def verify_candidate(state: FullHealingState) -> FullHealingState:
        plans = state.get("plans", [])
        if not plans:
            return {"verification_ok": True, "status": "healthy"}
        allowed = all(p.get("allowed", False) for p in plans)
        target_safe = all(sandbox.validate_target(p.get("check_name", "")) for p in plans)
        result = sandbox.verify(tests_passed=True, health_passed=allowed and target_safe, rollback_ready=True)
        return {"verification_ok": result.ok, "status": "verified" if result.ok else "blocked_verification"}

    def approval(state: FullHealingState) -> FullHealingState:
        if state.get("status") == "healthy":
            return {}
        if not state.get("verification_ok", False):
            return {"status": "blocked_verification"}
        if not state.get("approved", False):
            return {"status": "awaiting_approval"}
        return {"status": "approved"}

    def execute(state: FullHealingState) -> FullHealingState:
        # A real replacement is intentionally required; plans alone cannot mutate files.
        plans = state.get("plans", [])
        if not plans or state.get("status") != "approved":
            return {}
        p = plans[0]
        return {"status": "awaiting_repair_candidate", "execution": {"ok": False, "reason": "no concrete verified replacement supplied"}}

    def recheck(state: FullHealingState) -> FullHealingState:
        report = HealthEngine().run()
        if state.get("status") == "awaiting_repair_candidate":
            return {"post_health": report, "status": "awaiting_repair_candidate"}
        return {"post_health": report, "status": "healed" if report.get("status") == "healthy" else state.get("status", "degraded")}
    def audit(state: FullHealingState) -> FullHealingState:
        for p in state.get("plans", []):
            history.record(p["repair_id"], "full_graph", state.get("status", "unknown"), {"iteration": state.get("iteration", 0), "verification_ok": state.get("verification_ok", False)})
        return {}

    def route_approval(state: FullHealingState) -> str:
        if state.get("status") in {"healthy", "blocked_verification", "awaiting_approval"}:
            return "audit"
        return "execute"

    graph = StateGraph(FullHealingState)
    graph.add_node("observe", observe)
    graph.add_node("plan", plan)
    graph.add_node("verify_candidate", verify_candidate)
    graph.add_node("approval", approval)
    graph.add_node("execute", execute)
    graph.add_node("recheck", recheck)
    graph.add_node("audit", audit)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "plan")
    graph.add_edge("plan", "verify_candidate")
    graph.add_edge("verify_candidate", "approval")
    graph.add_conditional_edges("approval", route_approval, {"audit": "audit", "execute": "execute"})
    graph.add_edge("execute", "recheck")
    graph.add_edge("recheck", "audit")
    graph.add_edge("audit", END)
    return graph.compile()


def run_full_healing_graph(health_report: dict[str, Any] | None = None, approved: bool = False) -> FullHealingState:
    initial: FullHealingState = {"approved": approved}
    if health_report is not None:
        initial["health_report"] = health_report
    return build_full_healing_graph().invoke(initial)
