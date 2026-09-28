from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DATA = ROOT / "data"
EVIDENCE = DATA / "apex_parallel"
HIST = DATA / "apex_release_state.json"

def utc():
    return datetime.now(timezone.utc).isoformat()

def run_pytest(label, args, timeout=1800):
    tmp = ROOT / ".apex_tmp" / label
    if tmp.exists(): shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    # Keep Windows TEMP stable; isolate pytest with --basetemp instead.
    cmd = [str(PYTHON), "-m", "pytest", *args, "--basetemp", str(tmp / "pytest")]
    started = time.time()
    out_file = EVIDENCE / f"{label}.out"
    err_file = EVIDENCE / f"{label}.err"
    with out_file.open("w", encoding="utf-8") as out, err_file.open("w", encoding="utf-8") as err:
        try:
            p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=out, stderr=err)
            code = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            code = 124
    stdout = out_file.read_text(encoding="utf-8", errors="replace")
    stderr = err_file.read_text(encoding="utf-8", errors="replace")
    return {"layer": label, "returncode": code,
            "status": "PASS" if code == 0 else ("TIMEOUT" if code == 124 else "FAIL"),
            "duration_s": round(time.time()-started, 2),
            "stdout_tail": stdout[-6000:], "stderr_tail": stderr[-6000:]}

def main():
    DATA.mkdir(exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    historical = {}
    if HIST.exists():
        try: historical = json.loads(HIST.read_text(encoding="utf-8"))
        except Exception: historical = {"status": "unreadable"}
    layers = []
    layers.append(run_pytest("layer1_smoke", ["tests/test_api_watchdog.py",
        "tests/test_omega_credential_preflight.py",
        "tests/test_omega_credential_store.py"]))
    layers.append(run_pytest("layer2_runtime", ["tests/test_api_watchdog.py",
        "tests/test_self_healing_graph.py",
        "tests/test_apex_production_certification.py"]))
    layers.append(run_pytest("layer3_integration", ["tests/test_omega_live_validation.py",
        "tests/test_apex_production_certification.py"]))
    layers.append(run_pytest("layer4_full", ["tests"]))
    snapshot = {"captured_at": utc(), "historical": historical,
                "historical_preserved": True, "layers": layers}
    (EVIDENCE / "latest.json").write_text(json.dumps(snapshot, indent=2),
                                           encoding="utf-8")
    print(json.dumps(snapshot, indent=2))
    return 0 if all(x["status"] == "PASS" for x in layers) else 2

if __name__ == "__main__":
    raise SystemExit(main())
