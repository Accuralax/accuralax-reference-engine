from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "apex_parallel"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

GROUPS = {
    "A30_security_tenant": [
        "tests/test_credential_isolation.py",
        "tests/test_tenant_access.py",
        "tests/test_omega14_global_multitenant.py",
        "tests/test_omega_credential_preflight.py",
    ],
    "A31_observability_audit": [
        "tests/test_execution_audit.py",
        "tests/test_evidence_verifier.py",
        "tests/test_enterprise_state.py",
        "tests/test_runtime_control_plane.py",
    ],
    "A32_release_runtime": [
        "tests/test_apex_production_certification.py",
        "tests/test_runtime_release_gate.py",
        "tests/test_apex_omega_remaining.py",
        "tests/test_omega15_enterprise_final.py",
    ],
}

def run_group(name: str, files: list[str]) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    for key in (
        "HUBSPOT_ACCESS_TOKEN", "MAKE_API_TOKEN", "MAKE_WEBHOOK_URL",
        "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    ):
        env.pop(key, None)
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", *files, "-q", "--disable-warnings"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180,
    )
    output = (proc.stdout + proc.stderr).strip()
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "files": files,
        "output_tail": output[-2000:],
    }

def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    groups = {name: run_group(name, files) for name, files in GROUPS.items()}
    live_env = {
        key: bool(os.getenv(key))
        for key in (
            "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
            "HUBSPOT_ACCESS_TOKEN", "MAKE_API_TOKEN", "MAKE_WEBHOOK_URL",
        )
    }
    result = {
        "stage": "APEX-A30→A33→Ω",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "OFFLINE_CERTIFICATION",
        "groups": groups,
        "security": {
            "credential_values_exposed": False,
            "provider_credentials_used": False,
            "fail_closed": True,
        },
        "live_provider_environment": {
            "present": [k for k, v in live_env.items() if v],
            "missing": [k for k, v in live_env.items() if not v],
        },
        "release_policy": {
            "offline_evidence_can_certify_hardening": True,
            "offline_evidence_cannot_certify_live_providers": True,
            "release_allowed": False,
        },
    }
    result["status"] = "CERTIFIED_OFFLINE" if all(g["status"] == "PASS" for g in groups.values()) else "FAILED"
    canonical = json.dumps(result, sort_keys=True).encode()
    result["sha256"] = hashlib.sha256(canonical).hexdigest()
    out = DATA / "apex_offline_production_certification.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "CERTIFIED_OFFLINE" else 2

if __name__ == "__main__":
    raise SystemExit(main())
