from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / "watchdog"
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / "watchdog.lock"
EVENTS_FILE = STATE_DIR / "events.jsonl"
DEFAULT_URL = os.getenv("API_HEALTH_URL", "http://127.0.0.1:8788/health")


def healthy(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def _write_event(event: str, **details: object) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.time(), "event": str(event), **details}
    with EVENTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_state(**updates: object) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
    state.update(updates)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state


def acquire_lock() -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            owner = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            os.kill(owner, 0)
            return False
        except (OSError, ValueError):
            try:
                LOCK_FILE.unlink()
            except OSError:
                return False
            return acquire_lock()


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def start_server(port: int | None = None) -> subprocess.Popen:
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    env = os.environ.copy()
    if port is not None: env["CREATIVE_API_PORT"] = str(port)
    return subprocess.Popen([str(python), "-m", "src.api_server"], cwd=ROOT, env=env)


def stop_owned_process(process: subprocess.Popen | None, timeout: float = 5.0) -> None:
    """Stop and reap only the child process owned by this watchdog."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=max(timeout, 0.1))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=max(timeout, 0.1))


def child_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def status_snapshot() -> dict:
    state = read_state()
    owner_pid = None
    if LOCK_FILE.exists():
        try:
            owner_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
    child_pid = state.get("child_pid")
    return {
        "watchdog_pid": owner_pid,
        "watchdog_running": child_alive(owner_pid),
        "child_pid": child_pid,
        "child_alive": child_alive(child_pid),
        "status": state.get("status", "unknown"),
        "healthy": state.get("healthy"),
        "restart_count": state.get("restart_count", 0),
        "consecutive_failures": state.get("consecutive_failures", 0),
        "last_check": state.get("last_check"),
        "last_restart": state.get("last_restart"),
    }


def supervise(
    url: str,
    interval: float,
    startup_timeout: float,
    once: bool,
    *,
    health_fn=None,
    start_fn=None,
    sleep_fn=None,
    max_cycles: int | None = None,
) -> int:
    """Run the single-instance supervisor, with injectable dependencies for safe recovery tests."""
    check_health = health_fn or healthy
    launch_server = start_fn or start_server
    pause = sleep_fn or time.sleep
    if once:
        ok = check_health(url)
        _write_state(last_check=time.time(), healthy=ok, consecutive_failures=0 if ok else 1)
        _write_event("health_check", healthy=ok)
        return 0 if ok else 1
    if not acquire_lock():
        _write_event("watchdog_already_running")
        return 0
    process: subprocess.Popen | None = None
    restarts = 0
    consecutive_failures = 0
    cycles = 0
    was_healthy = False
    _write_state(started_at=time.time(), pid=os.getpid(), status="running", restart_count=0, consecutive_failures=0)
    _write_event("watchdog_started", pid=os.getpid())
    try:
        while True:
            cycles += 1
            if max_cycles is not None and cycles > max_cycles:
                return 0
            if check_health(url):
                consecutive_failures = 0
                _write_state(last_check=time.time(), healthy=True, status="healthy", restart_count=restarts, consecutive_failures=0)
                if not was_healthy:
                    _write_event("health_recovered", restart_count=restarts)
                was_healthy = True
                if max_cycles is not None:
                    return 0
                pause(interval)
                continue
            was_healthy = False
            consecutive_failures += 1
            _write_state(last_check=time.time(), healthy=False, status="recovering", restart_count=restarts, consecutive_failures=consecutive_failures)
            _write_event("health_failure", consecutive_failures=consecutive_failures)
            if process is not None and process.poll() is None:
                pause(interval)
                continue
            process = launch_server()
            restarts += 1
            _write_state(last_restart=time.time(), restart_count=restarts, child_pid=process.pid)
            _write_event("recovery_started", restart_count=restarts, child_pid=process.pid)
            deadline = time.monotonic() + startup_timeout
            while time.monotonic() < deadline:
                if check_health(url):
                    consecutive_failures = 0
                    was_healthy = True
                    _write_state(last_check=time.time(), healthy=True, status="healthy", restart_count=restarts, child_pid=process.pid, consecutive_failures=0)
                    _write_event("health_recovered", restart_count=restarts, child_pid=process.pid)
                    break
                if process.poll() is not None:
                    _write_state(last_check=time.time(), healthy=False, status="failed", restart_count=restarts, child_pid=process.pid)
                    return 1
                pause(0.5)
            else:
                stop_owned_process(process)
                _write_state(last_check=time.time(), healthy=False, status="startup_timeout", restart_count=restarts, child_pid=process.pid)
                _write_event("recovery_failed", reason="startup_timeout", restart_count=restarts, child_pid=process.pid)
                return 1
            if max_cycles is not None:
                return 0
            pause(interval)
    finally:
        release_lock()
        _write_state(stopped_at=time.time(), status="stopped")


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-instance local API health supervisor.")
    parser.add_argument("--once", action="store_true", help="check health once; never start a server")
    parser.add_argument("--status", action="store_true", help="print persisted watchdog ownership and health state")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status_snapshot(), indent=2, sort_keys=True))
        return 0
    return supervise(args.url, max(args.interval, 1.0), max(args.startup_timeout, 2.0), args.once)

if __name__ == "__main__":
    raise SystemExit(main())
