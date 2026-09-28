from __future__ import annotations
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
GATE = ROOT / "ops" / "apex_release_gate.py"


def main() -> int:
    total = 24
    for n in range(5, total + 1):
        print(f"APEX_REMAINING_START={n}", flush=True)
        p = subprocess.Popen([str(PYTHON), str(GATE), str(n)], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        started = time.monotonic()
        while p.poll() is None:
            time.sleep(2)
            if time.monotonic() - started >= 10:
                print(f"APEX_REMAINING_HEARTBEAT={n}", flush=True)
                started = time.monotonic()
        output, _ = p.communicate()
        print(output, end="")
        if p.returncode:
            print(f"APEX_REMAINING=FAILED_AT_{n}", flush=True)
            return p.returncode
    print("APEX_REMAINING=PASSED BATCHES=20", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
