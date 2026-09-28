from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
from typing import Any, Callable

from .health import HealthEngine
from .repair import RepairPlanner
from .repair_executor import RepairCandidate, RepairExecutor
from .sandbox import SandboxVerifier


@dataclass(frozen=True)
class DevelopmentCandidate:
    candidate_id: str
    target: str
    replacement: str
    fingerprint: str
    tests: tuple[str, ...]


class ApexAutonomousDevelopment:
    """Bounded self-development loop: observe -> diagnose -> sandbox -> evaluate -> approve -> promote."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        max_tests: int = 20,
        test_timeout: int = 60,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.root = Path(project_root).resolve()
        self.max_tests = max(1, min(int(max_tests), 100))
        self.test_timeout = max(5, min(int(test_timeout), 300))
        self.health = HealthEngine(self.root)
        self.planner = RepairPlanner()
        self.sandbox = SandboxVerifier()
        self.executor = RepairExecutor(self.root)
        self.runner = runner or subprocess.run
        self.candidates: dict[str, DevelopmentCandidate] = {}
        self.events: list[dict[str, Any]] = []

    @staticmethod
    def _fingerprint(target: str, replacement: str) -> str:
        return hashlib.sha256(
            (target + "\0" + replacement).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _candidate_id(target: str, replacement: str) -> str:
        return "DEV-" + ApexAutonomousDevelopment._fingerprint(target, replacement)[:12].upper()

    def observe(self, health_report: dict[str, Any] | None = None) -> dict[str, Any]:
        report = health_report if health_report is not None else self.health.run()
        event = {"stage": "observe", "status": report.get("status", "unknown"), "score": report.get("score")}
        self.events.append(event)
        return {"status": "observed", "health": report, "event": event}

    def diagnose(self, health_report: dict[str, Any]) -> dict[str, Any]:
        plans = self.planner.plan(health_report)
        result = {
            "status": "healthy" if not plans else "diagnosed",
            "repair_count": len(plans),
            "plans": [p.__dict__ for p in plans],
        }
        self.events.append({"stage": "diagnose", **result})
        return result

    def propose(self, target: str, replacement: str, tests: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
        if not self.sandbox.validate_target(target):
            return {"status": "blocked", "reason": "protected_target"}
        candidate_id = self._candidate_id(target, replacement)
        candidate = DevelopmentCandidate(
            candidate_id=candidate_id,
            target=target.replace("\\", "/"),
            replacement=replacement,
            fingerprint=self._fingerprint(target, replacement),
            tests=tuple(str(x) for x in tests)[: self.max_tests],
        )
        self.candidates[candidate_id] = candidate
        result = {"status": "proposed", "candidate": asdict(candidate)}
        self.events.append({"stage": "propose", "candidate_id": candidate_id, "status": "proposed"})
        return result

    def sandbox_verify(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.candidates.get(str(candidate_id))
        if not candidate:
            return {"status": "blocked", "reason": "candidate_not_found"}

        if not self.sandbox.validate_target(candidate.target):
            return {"status": "blocked", "reason": "protected_target"}

        sandbox_root = self.sandbox.create_sandbox(self.root)
        try:
            target = (sandbox_root / candidate.target).resolve()
            if sandbox_root not in target.parents or not target.is_file():
                return {"status": "blocked", "reason": "target_not_found_in_sandbox"}
            target.write_text(candidate.replacement, encoding="utf-8")

            tests = list(candidate.tests)
            if not tests:
                tests = ["tests"]
            command = [str(Path(__import__("sys").executable)), "-m", "pytest", "-q", *tests[: self.max_tests]]
            completed = self.runner(
                command,
                cwd=sandbox_root,
                capture_output=True,
                text=True,
                timeout=self.test_timeout,
            )
            passed = completed.returncode == 0
            result = {
                "status": "verified" if passed else "rejected",
                "verified": passed,
                "returncode": completed.returncode,
                "stdout_tail": (completed.stdout or "")[-4000:],
                "stderr_tail": (completed.stderr or "")[-2000:],
            }
            self.events.append({"stage": "sandbox", "candidate_id": candidate_id, "status": result["status"]})
            return result
        except subprocess.TimeoutExpired:
            result = {"status": "rejected", "verified": False, "reason": "sandbox_test_timeout"}
            self.events.append({"stage": "sandbox", "candidate_id": candidate_id, "status": "rejected", "reason": "timeout"})
            return result
        finally:
            shutil.rmtree(sandbox_root.parent, ignore_errors=True)

    def approve(self, candidate_id: str, actor_id: str, *, approved: bool = False) -> dict[str, Any]:
        if not approved:
            return {"status": "blocked", "reason": "approval_required"}
        if candidate_id not in self.candidates:
            return {"status": "blocked", "reason": "candidate_not_found"}
        result = {"status": "approved", "candidate_id": candidate_id, "approved_by": str(actor_id)}
        self.events.append({"stage": "approval", **result})
        return result

    def promote(self, candidate_id: str, *, approved: bool = False, verified: bool = False) -> dict[str, Any]:
        candidate = self.candidates.get(str(candidate_id))
        if not candidate:
            return {"status": "blocked", "reason": "candidate_not_found"}
        if not approved:
            return {"status": "blocked", "reason": "approval_required"}
        if not verified:
            return {"status": "blocked", "reason": "sandbox_verification_required"}

        repair = RepairCandidate(
            repair_id=candidate.candidate_id,
            target=candidate.target,
            replacement=candidate.replacement,
            fingerprint=candidate.fingerprint,
        )
        result = self.executor.execute(repair, approved=True, verified=True)
        output = {
            "status": "promoted" if result.applied else result.status,
            "applied": result.applied,
            "rolled_back": result.rolled_back,
            "reason": result.reason,
            "candidate_id": candidate_id,
        }
        self.events.append({"stage": "promote", "candidate_id": candidate_id, "status": output["status"]})
        return output

    def cycle(
        self,
        *,
        health_report: dict[str, Any] | None = None,
        target: str | None = None,
        replacement: str | None = None,
        tests: list[str] | tuple[str, ...] = (),
        approved: bool = False,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        observed = self.observe(health_report)
        diagnosis = self.diagnose(observed["health"])
        if diagnosis["status"] == "healthy":
            return {"status": "healthy", "observed": observed, "diagnosis": diagnosis}
        if target is None or replacement is None:
            return {"status": "awaiting_candidate", "observed": observed, "diagnosis": diagnosis}
        proposal = self.propose(target, replacement, tests)
        if proposal["status"] != "proposed":
            return {"status": "blocked", "proposal": proposal, "diagnosis": diagnosis}
        cid = proposal["candidate"]["candidate_id"]
        verification = self.sandbox_verify(cid)
        if not verification.get("verified"):
            return {"status": "blocked", "proposal": proposal, "verification": verification, "diagnosis": diagnosis}
        approval = self.approve(cid, actor_id or "human", approved=approved)
        if approval["status"] != "approved":
            return {"status": "awaiting_approval", "proposal": proposal, "verification": verification, "approval": approval}
        promotion = self.promote(cid, approved=True, verified=True)
        return {
            "status": promotion["status"],
            "proposal": proposal,
            "verification": verification,
            "approval": approval,
            "promotion": promotion,
            "diagnosis": diagnosis,
        }

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "bounded": True,
            "fail_closed": True,
            "proposal_boundary": True,
            "sandbox_required": True,
            "approval_required": True,
            "rollback": True,
            "max_tests": self.max_tests,
            "test_timeout": self.test_timeout,
            "candidate_count": len(self.candidates),
            "event_count": len(self.events),
        }
