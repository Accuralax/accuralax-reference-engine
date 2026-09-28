from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DATA = ROOT / "data"
REPORT = DATA / "apex_jt_release_report.json"

PHASES = [
    ("APEX-J", "Unattended production + watchdog/recovery + final evidence"),
    ("APEX-K", "Production deployment & environment convergence"),
    ("APEX-L", "Live integration activation — Supabase, API, workers, HubSpot/Make boundaries"),
    ("APEX-M", "Security hardening & penetration/regression verification"),
    ("APEX-N", "Observability, SLO/SLA, alerting & operational dashboards"),
    ("APEX-O", "Disaster recovery, backup/restore & regional recovery"),
    ("APEX-P", "Multi-tenant production hardening"),
    ("APEX-Q", "AI agent production certification & continuous evaluation"),
    ("APEX-R", "Autonomous operations/self-healing under governance"),
    ("APEX-S", "Enterprise readiness, documentation & operational handover"),
    ("APEX-T", "Final Production Release / Go-Live Gate"),
]

REQUIRED = [
    "ops/apex_supervisor.py",
    "ops/api_watchdog.py",
    "ops/recovery_probe.py",
    "ops/apex_release_gate.py",
    "ops/apex_run_all.py",
    "ops/run_apex_supervisor.ps1",
    "ops/run_api_watchdog.ps1",
    "ops/OVERNIGHT_RUNBOOK.md",
    "src/core/api_security.py",
    "src/core/supabase_runtime_adapter.py",
    "src/core/observability.py",
    "src/core/recovery_manager.py",
    "src/core/tenant_access.py",
    "src/core/agent_governance.py",
    "src/core/apex_production_certification.py",
    "src/core/apex_regression_gate.py",
    "src/core/apex_autonomous_runtime.py",
    "docs/SYSTEM_ARCHITECTURE.md",
    "docs/SELF_HEALING_LOOP.md",
]

ENV_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "HUBSPOT_ACCESS_TOKEN",
    "MAKE_API_TOKEN",
    "MAKE_WEBHOOK_URL",
    "API_AUTH_MODE",
    "API_API_KEY",
    "API_BEARER_TOKEN",
    "API_JWT_SECRET",
]


def run(*args: str, timeout: int = 900) -> tuple[int, str]:
    proc = subprocess.run(
        [str(PYTHON), *args],
        cwd=ROOT,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def check_files() -> dict:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing, "required_count": len(REQUIRED)}


def check_regression() -> dict:
    state_path = DATA / "apex_release_state.json"
    if not state_path.exists():
        return {"status": "FAIL", "reason": "apex_release_state.json missing"}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "FAIL", "reason": f"invalid release state: {exc}"}
    passed = state.get("status") == "passed"
    return {
        "status": "PASS" if passed else "FAIL",
        "state": state,
        "evidence": "636 tests previously recorded as passed" if passed and state.get("tests_passed") == 636 else None,
    }


def check_security_config() -> dict:
    mode = os.getenv("API_AUTH_MODE", "").strip().lower()
    api_key = bool(os.getenv("API_API_KEY"))
    bearer = bool(os.getenv("API_BEARER_TOKEN"))
    production_auth = mode in {"api_key", "bearer"} and (api_key if mode == "api_key" else bearer)
    return {
        "status": "PASS" if production_auth else "BLOCKED",
        "api_auth_mode": mode or "unset",
        "production_auth_configured": production_auth,
        "note": "Production must not run with API_AUTH_MODE=disabled/local.",
    }


def check_environment() -> dict:
    env = {}
    for key in ENV_KEYS:
        value = os.getenv(key)
        env[key] = "PRESENT" if value else "MISSING"
    return {
        "status": "PASS" if all(v == "PRESENT" for k, v in env.items() if k not in {"HUBSPOT_ACCESS_TOKEN", "MAKE_API_TOKEN", "MAKE_WEBHOOK_URL"}) else "BLOCKED",
        "keys": env,
        "note": "Values are never emitted.",
    }


def check_git() -> dict:
    code, out = run("-c", "import subprocess; print(subprocess.check_output(['git','status','--porcelain'], text=True))", timeout=30)
    return {"status": "PASS" if code == 0 and not out.strip() else "REVIEW", "status_output": out}


def build_report() -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "python": sys.version.split()[0],
        "repository": "Accuralax/accuralax-reference-engine",
        "phases": [{"phase": p, "focus": f} for p, f in PHASES],
        "checks": {
            "required_artifacts": check_files(),
            "regression_evidence": check_regression(),
            "security_configuration": check_security_config(),
            "environment_configuration": check_environment(),
            "git_worktree": check_git(),
        },
        "release_policy": {
            "go_live_requires": [
                "APEX-J through APEX-S evidence complete",
                "production authentication configured and verified",
                "live Supabase/API/worker integration verified",
                "HubSpot/Make boundaries verified with real credentials",
                "security and recovery gates passed",
                "multi-tenant isolation verified",
                "AI evaluation gate passed",
                "operator handover accepted",
            ],
            "fail_closed": True,
        },
    }
    checks = report["checks"]
    mandatory = [
        checks["required_artifacts"]["status"] == "PASS",
        checks["regression_evidence"]["status"] == "PASS",
        checks["security_configuration"]["status"] == "PASS",
        checks["environment_configuration"]["status"] == "PASS",
        checks["git_worktree"]["status"] == "PASS",
    ]
    report["overall_status"] = "READY_FOR_FINAL_GATE" if all(mandatory) else "BLOCKED"
    return report


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["overall_status"] == "READY_FOR_FINAL_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
