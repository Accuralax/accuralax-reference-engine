from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = {
    "worker_entrypoint": ROOT / "omega_worker.py",
    "worker_watchdog": ROOT / "ops" / "omega_worker_watchdog.py",
    "credential_store": ROOT / "ops" / "run_omega_worker_watchdog.ps1",
    "live_validation": ROOT / "ops" / "omega_live_validation.py",
    "release_gate": ROOT / "ops" / "apex_release_gate.py",
}


def main() -> int:
    result = {k: p.is_file() for k, p in CHECKS.items()}
    result["credentials_configured"] = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    result["git_remote_configured"] = False
    git_config = ROOT / ".git" / "config"
    if git_config.is_file():
        result["git_remote_configured"] = "[remote \"origin\"]" in git_config.read_text(encoding="utf-8", errors="ignore")
    result["production_release"] = all(result[k] for k in CHECKS) and result["credentials_configured"] and result["git_remote_configured"]
    print("OMEGA_RELEASE_READINESS=" + ("READY" if result["production_release"] else "BLOCKED"))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
