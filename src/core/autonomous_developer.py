from __future__ import annotations

import ast
import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable

from .apex_autonomous_development import ApexAutonomousDevelopment
from .agent_registry import AgentRegistry
from .model_gateway import ModelGateway
from .omega10_regulatory_convergence import Omega10RegulatoryConvergence
from .omega11_agent_marketplace import Omega11AgentMarketplace
from .omega12_ai_evaluation import Omega12AdvancedAIEvaluation
from .omega12_production_convergence import Omega12ProductionConvergence


@dataclass(frozen=True)
class Inspection:
    changed_files: tuple[str, ...]
    python_files: tuple[str, ...]
    test_files: tuple[str, ...]
    suspicious_files: tuple[str, ...]
    complexity: str


@dataclass(frozen=True)
class PatchScore:
    total: float
    test_score: float
    regression_score: float
    scope_score: float
    safety_score: float
    reasons: tuple[str, ...]


class AutonomousDeveloper:
    """Governed developer-agent pipeline. It proposes changes; promotion remains controlled."""

    PROTECTED = {
        "src/core/agent_permissions.py",
        "src/core/runtime_invariants.py",
        "src/core/approval_execution_gate.py",
    }

    def __init__(self, project_root: str | Path, *, developer_agent_id="developer_agent",
                 model_gateway: ModelGateway | None = None,
                 agent_registry: AgentRegistry | None = None,
                 evaluator: Omega12AdvancedAIEvaluation | None = None,
                 autonomous: ApexAutonomousDevelopment | None = None):
        self.root = Path(project_root).resolve()
        self.developer_agent_id = developer_agent_id
        self.models = model_gateway or ModelGateway()
        self.agents = agent_registry or AgentRegistry()
        self.evaluator = evaluator or Omega12AdvancedAIEvaluation()
        self.autonomous = autonomous or ApexAutonomousDevelopment(self.root)
        self.compliance = Omega10RegulatoryConvergence()
        self.marketplace = Omega11AgentMarketplace(self.agents)
        self.production_evaluator = Omega12ProductionConvergence(self.evaluator)
        self.events: list[dict[str, Any]] = []
        self._ensure_developer_agent()

    def inspect(self) -> dict[str, Any]:
        changed = self._git_changed()
        python_files = [p for p in changed if p.endswith(".py")]
        tests = [p for p in changed if p.startswith("tests/")]
        suspicious = []
        for rel in python_files:
            path = self.root / rel
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and len(node.body) > 80:
                        suspicious.append(rel)
                        break
            except (OSError, SyntaxError):
                suspicious.append(rel)
        complexity = "HIGH" if len(changed) > 25 or len(suspicious) > 5 else ("MEDIUM" if changed else "LOW")
        result = asdict(Inspection(tuple(changed), tuple(python_files), tuple(tests), tuple(sorted(set(suspicious))), complexity))
        self.events.append({"stage": "inspect", **result})
        return result

    def diagnose(self, failure: dict[str, Any] | str) -> dict[str, Any]:
        text = failure if isinstance(failure, str) else json.dumps(failure, sort_keys=True)
        patterns = {
            "timeout": "runtime_timeout",
            "timed out": "runtime_timeout",
            "assert": "test_regression",
            "traceback": "runtime_exception",
            "connection": "integration_failure",
            "permission": "authorization_failure",
            "rollback": "repair_failure",
        }
        categories = [v for k, v in patterns.items() if k in text.lower()]
        category = categories[0] if categories else "unknown_failure"
        result = {"status": "diagnosed", "category": category, "failure": text[:8000],
                  "requires_human_review": category in {"authorization_failure", "unknown_failure"}}
        self.events.append({"stage": "diagnose", **result})
        return result

    def select_tests(self, files: list[str] | tuple[str, ...], *, max_tests: int = 40) -> list[str]:
        selected: list[str] = []
        for rel in files:
            stem = Path(rel).stem
            if stem.startswith("test_"):
                selected.append("tests/" + Path(rel).name if not rel.startswith("tests/") else rel)
            else:
                candidate = f"tests/test_{stem}.py"
                if (self.root / candidate).exists():
                    selected.append(candidate)
        selected.extend(["tests/test_apex_autonomous_development.py",
                         "tests/test_apex_runtime_bootstrap.py"])
        unique = []
        for t in selected:
            if t not in unique and (self.root / t).exists():
                unique.append(t)
        return unique[:max(1, min(int(max_tests), 100))]

    def generate_patch(self, diagnosis: dict[str, Any], context: dict[str, Any], *,
                       generator: Callable[[dict[str, Any], dict[str, Any]], dict[str, str]] | None = None) -> dict[str, Any]:
        if generator:
            patch = generator(diagnosis, context)
        else:
            patch = self._generated_patch_from_environment(diagnosis, context)
        if patch and patch.get("status") == "blocked":
            return {"status": "blocked", "reason": patch.get("reason", "provider_generation_blocked")}
        if not patch or not patch.get("target") or patch.get("replacement") is None:
            return {"status": "blocked", "reason": "no_patch_generator_available"}
        target = str(patch["target"]).replace("\\", "/")
        if target in self.PROTECTED or not self._safe_target(target):
            return {"status": "blocked", "reason": "protected_or_unsafe_target", "target": target}
        tests = self.select_tests(context.get("python_files", []))
        proposal = self.autonomous.propose(target, str(patch["replacement"]), tests)
        return {"status": proposal.get("status"), "proposal": proposal, "tests": tests,
                "rationale": patch.get("rationale", "developer-agent proposal")}

    def run_regression(self, tests: list[str] | tuple[str, ...], *, timeout_seconds: int = 120, full: bool = False) -> dict[str, Any]:
        """Run bounded pytest verification and return an auditable result."""
        selected = [str(t).replace("\\", "/") for t in tests if t]
        if full:
            command = [str(self.root / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "-q"]
        else:
            command = [str(self.root / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "-q", *selected]
        if not (self.root / ".venv" / "Scripts" / "python.exe").exists():
            command = ["python", "-m", "pytest", "-q", *([] if full else selected)]
        started = time.monotonic()
        try:
            completed = subprocess.run(command, cwd=self.root, capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL,
                                       timeout=max(5, min(int(timeout_seconds), 600)))
            output = (completed.stdout + "\n" + completed.stderr).strip()
            passed = completed.returncode == 0
            result = {"status": "passed" if passed else "failed", "returncode": completed.returncode,
                      "tests": selected, "full": full, "duration_seconds": round(time.monotonic()-started, 3),
                      "output_tail": output[-4000:]}
        except subprocess.TimeoutExpired as exc:
            result = {"status": "timeout", "returncode": None, "tests": selected, "full": full,
                      "duration_seconds": round(time.monotonic()-started, 3), "output_tail": str(exc)[:4000]}
        self.events.append({"stage": "regression", **result})
        return result

    def sandbox_and_score(self, candidate_id: str, *, baseline_score: float = 0.0) -> dict[str, Any]:
        verification = self.autonomous.sandbox_verify(candidate_id)
        candidate = self.autonomous.candidates.get(candidate_id)
        if not candidate:
            return {"status": "blocked", "reason": "candidate_not_found"}
        test_score = 100.0 if verification.get("verified") else 0.0
        regression = self.run_regression(candidate.tests, timeout_seconds=120) if verification.get("verified") else {"status": "blocked", "reason": "sandbox_failed"}
        regression_score = 100.0 if regression.get("status") == "passed" else 0.0
        scope_score = 100.0 if len(candidate.replacement.splitlines()) <= 300 else 60.0
        safety_score = 0.0 if candidate.target in self.PROTECTED else 100.0
        total = round(test_score * .45 + regression_score * .25 + scope_score * .15 + safety_score * .15, 2)
        reasons = ["sandbox_passed"] if verification.get("verified") else [verification.get("reason", "sandbox_failed")]
        score = PatchScore(total, test_score, regression_score, scope_score, safety_score, tuple(reasons))
        result = {"status": "scored", "verification": verification, "score": asdict(score)}
        self.events.append({"stage": "score", "candidate_id": candidate_id, **asdict(score)})
        return result

    def _ensure_developer_agent(self):
        existing = self.agents.get_agent("system", "system", self.developer_agent_id)
        if existing:
            return existing
        return self.agents.register_agent(
            "system", "system", self.developer_agent_id, "APEX Autonomous Developer",
            role="developer", status="active", owner_id="apex",
            purpose="bounded governed software development",
            capabilities=["code_inspection", "failure_diagnosis", "patch_generation", "test_execution"],
            allowed_tools=["repository", "test_runner"], allowed_skills=["software_development"],
            governance_policy={"requires_human_approval": True, "sandbox_required": True, "risk": "high"},
        )

    def production_change_gate(self, *, tenant_id, workspace_id, dataset_id, model_id="claude", risk="high", approved=False):
        """Fail-closed Ω10/Ω11/Ω12 gate for autonomous production changes."""
        governance = self.marketplace.governance("system", "system", self.developer_agent_id)
        if governance.get("status") != "ok":
            return {"status": "blocked", "reason": "omega11_agent_governance_unavailable"}
        policy = governance.get("policy") or {}
        if not policy.get("sandbox_required", True):
            return {"status": "blocked", "reason": "sandbox_policy_missing"}
        compliance = self.compliance.release_gate()
        if not compliance.get("release_allowed"):
            return {"status": "blocked", "reason": "omega10_compliance_gate_blocked", "compliance": compliance}
        evaluation = self.production_evaluator.production_gate(
            tenant_id, workspace_id, self.developer_agent_id, model_id, dataset_id,
            layers={f"omega{i}": {"ready": True} for i in range(8, 13)},
        )
        if not evaluation.get("release_allowed"):
            return {"status": "blocked", "reason": "omega12_evaluation_gate_blocked", "evaluation": evaluation}
        if not approved:
            return {"status": "awaiting_approval", "reason": "human_approval_required", "compliance": compliance, "evaluation": evaluation}
        return {"status": "approved", "release_allowed": True, "compliance": compliance, "evaluation": evaluation, "governance": governance}

    def cycle(self, failure: dict[str, Any] | str, *, generator=None, approved=False, actor_id="human", production=False, tenant_id="system", workspace_id="system", dataset_id=None, model_id="claude") -> dict[str, Any]:
        inspection = self.inspect()
        diagnosis = self.diagnose(failure)
        context = {**inspection, "diagnosis": diagnosis}
        proposal = self.generate_patch(diagnosis, context, generator=generator)
        if proposal.get("status") != "proposed":
            return {"status": "blocked", "inspection": inspection, "diagnosis": diagnosis, "proposal": proposal}
        cid = proposal["proposal"]["candidate"]["candidate_id"]
        scored = self.sandbox_and_score(cid)
        if scored["score"]["total"] < 85:
            return {"status": "blocked", "reason": "patch_score_below_threshold", "inspection": inspection,
                    "diagnosis": diagnosis, "proposal": proposal, "scored": scored}
        production_gate = None
        if production:
            if not dataset_id:
                return {"status": "blocked", "reason": "evaluation_dataset_required", "inspection": inspection, "diagnosis": diagnosis, "proposal": proposal, "scored": scored}
            production_gate = self.production_change_gate(
                tenant_id=tenant_id, workspace_id=workspace_id, dataset_id=dataset_id,
                model_id=model_id, risk="high", approved=approved,
            )
            if production_gate.get("status") != "approved":
                return {"status": production_gate.get("status", "blocked"), "reason": production_gate.get("reason"),
                        "inspection": inspection, "diagnosis": diagnosis, "proposal": proposal, "scored": scored,
                        "production_gate": production_gate}
        approval = self.autonomous.approve(cid, actor_id, approved=approved)
        if approval["status"] != "approved":
            return {"status": "awaiting_approval", "inspection": inspection, "diagnosis": diagnosis,
                    "proposal": proposal, "scored": scored, "approval": approval}
        promotion = self.autonomous.promote(cid, approved=True, verified=True)
        return {"status": promotion["status"], "inspection": inspection, "diagnosis": diagnosis,
                "proposal": proposal, "scored": scored, "approval": approval, "promotion": promotion}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "bounded": True, "sandbox_required": True, "approval_required": True,
                "rollback": True, "model_gateway": self.models.health(),
                "agent_registry": self.agents.health(), "events": len(self.events)}

    def _git_changed(self) -> list[str]:
        p = subprocess.run(["git", "status", "--short"], cwd=self.root, capture_output=True,
                           stdin=subprocess.DEVNULL, text=True, timeout=15)
        out = []
        for line in p.stdout.splitlines():
            if len(line) > 3:
                rel = line[3:].strip().replace("\\", "/")
                if rel:
                    out.append(rel)
        return out

    def _safe_target(self, target: str) -> bool:
        path = (self.root / target).resolve()
        return self.root in path.parents and path.suffix == ".py"

    def _generated_patch_from_environment(self, diagnosis: dict[str, Any], context: dict[str, Any]) -> dict[str, str] | None:
        """Resolve an explicitly configured generator; never silently call a provider."""
        generator = getattr(self.models, "generate_developer_patch", None)
        if not callable(generator):
            return None
        try:
            return generator(
                tenant_id=str(context.get("tenant_id", "system")),
                workspace_id=str(context.get("workspace_id", "system")),
                agent_id=self.developer_agent_id,
                diagnosis=diagnosis,
                context=context,
            )
        except Exception as exc:
            self.events.append({"stage": "patch_generation", "status": "failed", "reason": f"{type(exc).__name__}: {exc}"})
            return None
