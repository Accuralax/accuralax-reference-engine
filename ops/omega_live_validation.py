from __future__ import annotations
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.omega_runtime_adapter import OmegaRuntimeAdapter


def main() -> int:
    adapter = OmegaRuntimeAdapter()
    if not adapter.enabled:
        print("OMEGA_LIVE_VALIDATION=BLOCKED")
        print("OMEGA_LIVE_ISSUE=CREDENTIALS_NOT_CONFIGURED")
        return 3
    checks = {}
    try:
        checks["health"] = adapter.health()
        checks["invariants"] = adapter.invariant_check()
        checks["worker_tick"] = adapter.worker_tick("OMEGA_CORE_WORKER", 20)
        checks["apex_tick"] = adapter.apex_tick()
        checks["health_after"] = adapter.health()
        checks["invariants_after"] = adapter.invariant_check()
    except Exception as exc:
        print("OMEGA_LIVE_VALIDATION=FAILED")
        print(f"OMEGA_LIVE_ISSUE={type(exc).__name__}")
        return 2
    print("OMEGA_LIVE_VALIDATION=PASSED")
    print(json.dumps(checks, default=str, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
