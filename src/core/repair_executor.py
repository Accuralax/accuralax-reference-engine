from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Any

from .controlled_repair import ControlledRepairApplier
from .sandbox import SandboxVerifier
from .repair_circuit import RepairCircuitBreaker
from .repair_history import SQLiteRepairHistory


@dataclass(frozen=True)
class RepairCandidate:
    repair_id: str
    target: str
    replacement: str
    fingerprint: str


@dataclass(frozen=True)
class RepairExecutionResult:
    status: str
    applied: bool
    rolled_back: bool
    reason: str
    repair_id: str


class RepairExecutor:
    """Execute only concrete, approved, sandbox-verified repair candidates."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.sandbox = SandboxVerifier()
        self.applier = ControlledRepairApplier(self.project_root)
        self.circuit = RepairCircuitBreaker(max_failures=3)
        self.history = SQLiteRepairHistory()

    @staticmethod
    def fingerprint(target: str, replacement: str) -> str:
        payload = json.dumps({"target": target, "replacement": replacement}, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def candidate(self, repair_id: str, target: str, replacement: str) -> RepairCandidate:
        if not self.sandbox.validate_target(target):
            raise PermissionError("repair target is protected")
        return RepairCandidate(repair_id, target, replacement, self.fingerprint(target, replacement))

    def execute(self, candidate: RepairCandidate, *, approved: bool, verified: bool) -> RepairExecutionResult:
        if not self.circuit.allow(candidate.repair_id):
            result = RepairExecutionResult("circuit_open", False, False, "repair circuit is open", candidate.repair_id)
            self.history.record(candidate.repair_id, "execution_blocked", result.status, {"reason": result.reason})
            return result
        if not approved:
            result = RepairExecutionResult("awaiting_approval", False, False, "human approval required", candidate.repair_id)
            self.history.record(candidate.repair_id, "execution_blocked", result.status, {"reason": result.reason})
            return result
        if not verified:
            result = RepairExecutionResult("verification_required", False, False, "sandbox verification required", candidate.repair_id)
            self.history.record(candidate.repair_id, "execution_blocked", result.status, {"reason": result.reason})
            return result
        result = self.applier.apply(candidate.target, candidate.replacement, approved=True, verified=True)
        if result.ok:
            self.circuit.record_success(candidate.repair_id)
            self.history.record(candidate.repair_id, "execution_applied", "success", {"target": candidate.target, "fingerprint": candidate.fingerprint})
            return RepairExecutionResult("applied", True, False, result.reason, candidate.repair_id)
        self.circuit.record_failure(candidate.repair_id, result.reason)
        self.history.record(candidate.repair_id, "execution_rolled_back", "rollback", {"target": candidate.target, "fingerprint": candidate.fingerprint})
        return RepairExecutionResult("rolled_back", False, True, result.reason, candidate.repair_id)
