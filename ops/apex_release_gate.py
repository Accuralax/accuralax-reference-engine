from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
FILES = sorted((ROOT / "tests").glob("test_*.py"), key=lambda p: p.name)
BATCH = 6

def main() -> int:
    if len(sys.argv) == 1:
        print(f"APEX_GATE_INFO FILES={len(FILES)} BATCH_SIZE={BATCH} BATCHES={(len(FILES)+BATCH-1)//BATCH}")
        return 0
    n = int(sys.argv[1])
    start = (n - 1) * BATCH
    group = FILES[start:start + BATCH]
    if not group:
        print(f"APEX_BATCH_EMPTY={n}")
        return 0
    print(f"APEX_BATCH_START={n} FILES={len(group)}", flush=True)
    for p in group:
        print(f"APEX_FILE={p.name}", flush=True)
    result = subprocess.run([str(PYTHON), "-m", "pytest", "-q", *map(str, group)], cwd=ROOT)
    print(f"APEX_BATCH_RESULT={n} EXIT={result.returncode}", flush=True)
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
