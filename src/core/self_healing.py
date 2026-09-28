from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .health import HealthEngine
from .repair import RepairPlanner
from .repair_circuit import RepairCircuitBreaker
from .repair_history import SQLiteRepairHistory


@dataclass(frozen=True)
class SelfHealingResult:
    status: str
    health_status: str
    repair_count: int
    blocked_count: int
    circuit_open_count: int
    audit_events: int


class SelfHealingOrchestrator:
    """Connect observation, planning, circuit protection and durable audit without auto-applying repairs."""

    def __init__(self, project_root: str, history_path: str = "data/repairs.sqlite3", max_failures: int = 3):
        self.project_root = project_root
        self.planner = RepairPlanner()
        self.circuit = RepairCircuitBreaker(max_failures=max_failures)
        self.history = SQLiteRepairHistory(history_path)

    def run(self, health_report: dict[str, Any]) -> SelfHealingResult:
        plans = self.planner.plan(health_report)
        blocked = 0
        open_circuits = 0
        for plan in plans:
            self.history.record(plan.repair_id, "repair_planned", "planned", {"check": plan.check_name, "risk": plan.risk})
            if not plan.allowed:
                blocked += 1
                self.history.record(plan.repair_id, "repair_blocked", "approval_required", {"risk": plan.risk})
                continue
            if not self.circuit.allow(plan.repair_id):
                open_circuits += 1
                self.history.record(plan.repair_id, "repair_blocked", "circuit_open")
                continue
            self.history.record(plan.repair_id, "repair_ready", "awaiting_approval")
        status = "healthy" if not plans else "repair_review_required"
        return SelfHealingResult(status, str(health_report.get("status", "unknown")), len(plans), blocked, open_circuits, len(self.history.list()))
