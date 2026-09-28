from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
GATE = ROOT / "ops" / "apex_release_gate.py"

def main() -> int:
    info = subprocess.run([str(PYTHON), str(GATE)], cwd=ROOT)
    if info.returncode:
        return info.returncode
    files = sorted((ROOT / "tests").glob("test_*.py"))
    batch = 6
    total = (len(files) + batch - 1) // batch
    for n in range(1, total + 1):
        result = subprocess.run([str(PYTHON), str(GATE), str(n)], cwd=ROOT)
        if result.returncode:
            print(f"APEX_ALL_BATCHES=FAILED_AT_{n}")
            return result.returncode
    print(f"APEX_ALL_BATCHES=PASSED TOTAL={total}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
