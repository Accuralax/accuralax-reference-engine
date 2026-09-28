from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
FILES = sorted((ROOT / "tests").glob("test_*.py"), key=lambda p: p.name)
BATCH = 6
ENV = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "--import-mode=importlib"}
LOG = ROOT / "data" / "apex_release_gate.log"


def run(args: list[str]) -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        result = subprocess.run([str(PYTHON), *args], cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    return result.returncode


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
    batch_tmp = ROOT / ".apex_tmp" / f"release_batch_{n}"
    batch_tmp.mkdir(parents=True, exist_ok=True)
    code = run(["-m", "pytest", "-q", "--basetemp", str(batch_tmp), *map(str, group)])
    print(f"APEX_BATCH_RESULT={n} EXIT={code}", flush=True)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
