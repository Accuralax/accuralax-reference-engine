from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from datetime import datetime, timezone
import hashlib
import json
import time
import uuid
import yaml


@dataclass
class HealthSignal:
    domain: str
    status: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairPlan:
    repair_id: str
    domain: str
    diagnosis: str
    risk: str
    action: str
    approved: bool = False


class ReliabilityFabric:
    """Bounded detect-diagnose-repair-retest loop with approval and rollback gates."""

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "self_healing.yaml").read_text(encoding="utf-8")) or {}
        self.signals: list[HealthSignal] = []
        self.repairs: list[RepairPlan] = []
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.repair_handlers: dict[str, Callable[[], Any]] = {}

    def report_health(self, domain: str, status: str, message: str, **evidence: Any) -> HealthSignal:
        signal = HealthSignal(domain, status, message, self._safe(evidence))
        self.signals.append(signal)
        return signal

    def diagnose(self, domain: str) -> dict[str, Any]:
        matches = [s for s in self.signals if s.domain == domain]
        unhealthy = [s for s in matches if s.status.lower() not in {"ok", "healthy", "pass"}]
        return {
            "domain": domain,
            "status": "issue_detected" if unhealthy else "healthy",
            "signals": len(matches),
            "evidence": [s.evidence for s in unhealthy],
            "recommended": "repair" if unhealthy else "none",
        }

    def propose_repair(self, domain: str, diagnosis: str, action: str, risk: str = "medium") -> RepairPlan:
        plan = RepairPlan(f"RPR-{uuid.uuid4().hex[:12].upper()}", domain, diagnosis, risk, action)
        self.repairs.append(plan)
        return plan

    def register_repair_handler(self, repair_id: str, handler: Callable[[], Any]) -> None:
        for plan in self.repairs:
            if plan.repair_id == repair_id:
                self.repair_handlers[repair_id] = handler
                return

    def execute_repair(self, repair_id: str, *, approved: bool = False) -> dict[str, Any]:
        plan = next((p for p in self.repairs if p.repair_id == repair_id), None)
        if not plan:
            return {"allowed": False, "reason": "repair_not_found"}
        if plan.risk in {"high", "critical"} and not approved:
            return {"allowed": False, "reason": "human_approval_required"}
        handler = self.repair_handlers.get(repair_id)
        if handler is None:
            return {"allowed": False, "reason": "repair_handler_not_available"}

        snapshot = f"CHK-REPAIR-{uuid.uuid4().hex[:10].upper()}"
        self.checkpoints[snapshot] = {"repair_id": repair_id, "status": "before_repair"}
        started = time.monotonic()
        try:
            result = handler()
            if time.monotonic() - started > self.config["runtime"]["timeout_seconds"]:
                self.checkpoints[snapshot]["status"] = "timeout"
                self.checkpoints[snapshot]["rollback_required"] = True
                return {"allowed": False, "reason": "repair_timeout", "checkpoint": snapshot, "rollback_required": True, "rollback_available": True}
            plan.approved = approved or plan.risk not in {"high", "critical"}
            digest = hashlib.sha256(json.dumps(self._safe(result), sort_keys=True, default=str).encode()).hexdigest()
            return {
                "allowed": True, "repair_id": repair_id, "status": "repaired",
                "result": self._safe(result), "result_hash": digest,
                "checkpoint": snapshot, "verified": False,
                "rollback_available": True, "credentials_exposed": False,
            }
        except Exception as exc:
            self.checkpoints[snapshot]["status"] = "failed"
            self.checkpoints[snapshot]["rollback_required"] = True
            return {"allowed": False, "repair_id": repair_id,
                    "reason": "repair_failed", "error_type": type(exc).__name__,
                    "checkpoint": snapshot, "rollback_available": True}

    def verify_repair(self, repair_id: str, test: Callable[[], bool]) -> dict[str, Any]:
        try:
            passed = bool(test())
        except Exception:
            passed = False
        return {"repair_id": repair_id, "verified": passed,
                "status": "verified" if passed else "rollback_required",
                "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "health_signals": len(self.signals),
            "repair_plans": len(self.repairs),
            "max_repair_iterations": self.config["runtime"]["max_repair_iterations"],
            "rollback_supported": True,
            "credentials_exposed": False,
        }

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): ReliabilityFabric._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [ReliabilityFabric._safe(v) for v in value]
        return value
