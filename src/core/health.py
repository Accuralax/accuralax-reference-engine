from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    message: str
    details: dict[str, Any]


class HealthEngine:
    """Deterministic, read-only health checks for the agent runtime."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2])

    def _file_check(self) -> HealthCheck:
        required = [
            "src/main.py", "src/crew.py", "src/core/langgraph_runtime.py",
            "src/core/agent_permissions.py", "src/core/business_gateway.py",
            "src/integrations/execution.py", "src/integrations/durable_ledger.py",
            "src/integrations/audited_router.py", "src/config/agent_permissions.yaml",
            "src/config/business_systems.yaml", "src/knowledge/services.yaml",
            "src/knowledge/service_knowledge.yaml", "src/knowledge/skills.yaml",
        ]
        missing = [p for p in required if not (self.root / p).exists()]
        return HealthCheck("files", "pass" if not missing else "fail", "Required runtime files present" if not missing else "Missing runtime files", {"missing": missing})

    def _python_check(self) -> HealthCheck:
        return HealthCheck("python", "pass", "Python runtime available", {"version": platform.python_version(), "executable": sys.executable})

    def _dependency_check(self) -> HealthCheck:
        proc = subprocess.run([sys.executable, "-m", "pip", "check"], cwd=self.root, capture_output=True, text=True, timeout=30)
        return HealthCheck("dependencies", "pass" if proc.returncode == 0 else "fail", proc.stdout.strip() or proc.stderr.strip(), {})

    def _config_check(self) -> HealthCheck:
        import yaml
        paths = ["src/config/agents.yaml", "src/config/tasks.yaml", "src/config/business_rules.yaml", "src/config/agent_permissions.yaml", "src/config/business_systems.yaml", "src/knowledge/services.yaml", "src/knowledge/service_knowledge.yaml", "src/knowledge/skills.yaml"]
        errors = []
        for rel in paths:
            try:
                with (self.root / rel).open("r", encoding="utf-8") as handle:
                    yaml.safe_load(handle)
            except Exception as exc:
                errors.append(f"{rel}: {type(exc).__name__}")
        return HealthCheck("configuration", "pass" if not errors else "fail", "YAML configuration valid" if not errors else "Configuration errors detected", {"errors": errors})

    def _ledger_check(self) -> HealthCheck:
        from src.integrations.durable_ledger import SQLiteExecutionLedger
        ledger = SQLiteExecutionLedger(self.root / "data" / "executions.sqlite3")
        return HealthCheck("execution_ledger", "pass", "Execution ledger accessible", {"records": ledger.count(), "path": str(ledger.path)})

    def _permissions_check(self) -> HealthCheck:
        import yaml
        path = self.root / "src/config/agent_permissions.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        policy = data.get("policy", {})
        ok = policy.get("default_tool_access") == "deny" and policy.get("credentials_never_exposed_to_agents") is True and policy.get("repair_requires_human_approval") is True
        return HealthCheck("agent_permissions", "pass" if ok else "fail", "Critical permission guardrails active" if ok else "Critical permission guardrail missing", {"default_tool_access": policy.get("default_tool_access"), "repair_requires_human_approval": policy.get("repair_requires_human_approval"), "credentials_never_exposed_to_agents": policy.get("credentials_never_exposed_to_agents")})

    def _business_gateway_check(self) -> HealthCheck:
        import yaml
        data = yaml.safe_load((self.root / "src/config/business_systems.yaml").read_text(encoding="utf-8"))
        policy = data.get("policy", {})
        ok = policy.get("default_action") == "deny" and policy.get("require_idempotency") is True and policy.get("external_side_effects_require_approval") is True
        return HealthCheck("business_gateway", "pass" if ok else "fail", "Business capability guardrails active" if ok else "Business capability guardrail missing", {"default_action": policy.get("default_action"), "require_idempotency": policy.get("require_idempotency"), "external_side_effects_require_approval": policy.get("external_side_effects_require_approval")})

    def run(self) -> dict[str, Any]:
        checks = [self._file_check(), self._python_check(), self._dependency_check(), self._config_check(), self._ledger_check(), self._permissions_check(), self._business_gateway_check()]
        failed = sum(c.status == "fail" for c in checks)
        score = round((len(checks) - failed) / len(checks) * 100)
        return {"status": "healthy" if failed == 0 else "degraded", "score": score, "checks": [asdict(c) for c in checks]}
