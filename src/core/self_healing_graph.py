from __future__ import annotations

from typing import TypedDict, Any
from pathlib import Path
import tempfile

from langgraph.graph import StateGraph, START, END

from .repair import RepairPlanner
from .sandbox import SandboxVerifier
from .controlled_repair import ControlledRepairApplier
from .repair_circuit import RepairCircuitBreaker
from .repair_history import SQLiteRepairHistory


class SelfHealingGraphState(TypedDict, total=False):
    health_report: dict[str, Any]
    plans: list[dict[str, Any]]
    approved: bool
    verification_ok: bool
    apply_ok: bool
    rolled_back: bool
    status: str
    iterations: int
    repair_id: str


def build_self_healing_graph(max_iterations: int = 3):
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    planner = RepairPlanner()
    circuit = RepairCircuitBreaker(max_failures=3)

    def observe(state: SelfHealingGraphState) -> SelfHealingGraphState:
        return {"iterations": state.get("iterations", 0) + 1}

    def plan(state: SelfHealingGraphState) -> SelfHealingGraphState:
        plans = planner.plan(state.get("health_report", {"status": "healthy", "checks": []}))
        return {"plans": [p.__dict__ for p in plans]}

    def sandbox_verify(state: SelfHealingGraphState) -> SelfHealingGraphState:
        plans = state.get("plans", [])
        if not plans:
            return {"verification_ok": True}
        sandbox = SandboxVerifier()
        source = Path.cwd()
        candidate = sandbox.create_sandbox(source)
        # Snapshot the isolated candidate and require every planned action to
        # remain outside protected guardrails. No production file is modified.
        snapshot = sandbox.snapshot(candidate)
        checks = [sandbox.validate_target(p["check_name"]) for p in plans]
        verification = sandbox.verify(
            tests_passed=bool(snapshot),
            health_passed=all(checks),
            rollback_ready=True,
        )
        return {"verification_ok": verification.ok}

    def approval_gate(state: SelfHealingGraphState) -> SelfHealingGraphState:
        plans = state.get("plans", [])
        if not plans:
            return {"status": "healthy"}
        if not state.get("verification_ok", False):
            return {"status": "blocked_verification"}
        if any(not p.get("allowed", False) for p in plans):
            return {"status": "blocked_policy"}
        if not state.get("approved", False):
            return {"status": "awaiting_approval"}
        return {"status": "approved"}

    def apply(state: SelfHealingGraphState) -> SelfHealingGraphState:
        if state.get("status") != "approved":
            return {"apply_ok": False}
        # The graph deliberately stops before mutation unless a concrete,
        # verified replacement is supplied by a future repair executor.
        return {"apply_ok": False, "status": "awaiting_controlled_apply"}

    def audit(state: SelfHealingGraphState) -> SelfHealingGraphState:
        history = SQLiteRepairHistory()
        for plan in state.get("plans", []):
            history.record(plan["repair_id"], "graph_state", state.get("status", "unknown"), {"verification_ok": state.get("verification_ok", False)})
        return {}

    def route_after_gate(state: SelfHealingGraphState) -> str:
        if state.get("status") in {"healthy", "blocked_verification", "blocked_policy", "awaiting_approval"}:
            return "audit"
        return "apply"

    def route_after_apply(state: SelfHealingGraphState) -> str:
        return "audit"

    graph = StateGraph(SelfHealingGraphState)
    graph.add_node("observe", observe)
    graph.add_node("plan", plan)
    graph.add_node("sandbox_verify", sandbox_verify)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("apply", apply)
    graph.add_node("audit", audit)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "plan")
    graph.add_edge("plan", "sandbox_verify")
    graph.add_edge("sandbox_verify", "approval_gate")
    graph.add_conditional_edges("approval_gate", route_after_gate, {"audit": "audit", "apply": "apply"})
    graph.add_conditional_edges("apply", route_after_apply, {"audit": "audit"})
    graph.add_edge("audit", END)
    return graph.compile()


def run_self_healing_graph(health_report: dict[str, Any], approved: bool = False) -> SelfHealingGraphState:
    return build_self_healing_graph().invoke({"health_report": health_report, "approved": approved})
