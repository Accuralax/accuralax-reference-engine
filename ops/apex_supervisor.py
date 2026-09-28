from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
LOG = ROOT / "data" / "apex_supervisor.log"
MAX_BACKOFF = 300


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def credential_store_ready() -> bool:
    return (ROOT / "data" / "omega-credentials.dpapi").is_file()


def command(name: str) -> list[str]:
    script = ROOT / "ops" / name
    return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]


def run(*, interval: float = 15.0, max_cycles: int | None = None) -> int:
    if not PYTHON.is_file():
        log("BLOCKED python_runtime_missing")
        return 2
    children: dict[str, subprocess.Popen] = {}
    backoff: dict[str, int] = {"api": 5, "omega": 5}
    cycles = 0
    try:
        while True:
            cycles += 1
            if max_cycles is not None and cycles > max_cycles:
                return 0
            desired = {"api": "run_api_watchdog.ps1"}
            if credential_store_ready():
                desired["omega"] = "run_omega_worker_watchdog.ps1"
            for name, script in desired.items():
                proc = children.get(name)
                if proc is None or proc.poll() is not None:
                    if proc is not None:
                        log(f"RESTART {name} exit={proc.returncode} backoff={backoff[name]}")
                        time.sleep(backoff[name])
                        backoff[name] = min(backoff[name] * 2, MAX_BACKOFF)
                    children[name] = subprocess.Popen(command(script), cwd=ROOT)
                    log(f"START {name} pid={children[name].pid}")
                else:
                    backoff[name] = 5
            for name in list(children):
                if name not in desired:
                    proc = children.pop(name)
                    if proc.poll() is None:
                        proc.terminate()
                    log(f"STOP {name} reason=credential_store_unavailable")
            time.sleep(max(2.0, min(float(interval), 300.0)))
    finally:
        for name, proc in children.items():
            if proc.poll() is None:
                proc.terminate()
            log(f"STOP {name}")


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        log("STOP supervisor_interrupted")
        raise SystemExit(130)
