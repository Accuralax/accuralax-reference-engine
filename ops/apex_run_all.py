from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
GATE = ROOT / "ops" / "apex_release_gate.py"
STATE = ROOT / "data" / "apex_release_state.json"


def main() -> int:
    info = subprocess.run([str(PYTHON), str(GATE)], cwd=ROOT, capture_output=True, text=True)
    print(info.stdout, end="")
    if info.returncode:
        return info.returncode
    files = sorted((ROOT / "tests").glob("test_*.py"))
    batch = 6
    total = (len(files) + batch - 1) // batch
    state = {"status": "running", "total_batches": total, "completed_batches": [], "test_files": len(files)}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    for n in range(1, total + 1):
        result = subprocess.run([str(PYTHON), str(GATE), str(n)], cwd=ROOT, capture_output=True, text=True)
        print(result.stdout, end="")
        if result.returncode:
            state.update({"status": "failed", "failed_batch": n})
            STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(f"APEX_ALL_BATCHES=FAILED_AT_{n}")
            return result.returncode
        state["completed_batches"].append(n)
        STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    state["status"] = "passed"
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"APEX_ALL_BATCHES=PASSED TOTAL={total} FILES={len(files)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
