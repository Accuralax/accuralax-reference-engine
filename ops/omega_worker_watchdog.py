from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
WORKER = ROOT / "omega_worker.py"
LOG = ROOT / "data" / "omega_worker_watchdog.log"
MAX_BACKOFF = 300


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {message}\n")


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def run() -> int:
    if not PYTHON.is_file() or not WORKER.is_file():
        log("FATAL worker_runtime_missing")
        return 2
    if not configured():
        log("BLOCKED worker_credentials_not_configured")
        return 3
    delay = 5
    while True:
        log("START worker")
        proc = subprocess.Popen([str(PYTHON), str(WORKER)], cwd=str(ROOT))
        code = proc.wait()
        if code == 0:
            log("STOP worker_exit_clean")
            return 0
        log(f"FAIL worker_exit_code={code} restart_in={delay}s")
        time.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        log("STOP watchdog_interrupted")
        raise SystemExit(130)
