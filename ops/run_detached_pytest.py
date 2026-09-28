from __future__ import annotations
import subprocess, sys
from pathlib import Path

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

def main():
    root = Path(__file__).resolve().parents[1]
    label = sys.argv[1]
    args = sys.argv[2:]
    out = root / "data" / "apex_parallel" / f"{label}.out"
    err = root / "data" / "apex_parallel" / f"{label}.err"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as oh, err.open("w", encoding="utf-8") as eh:
        p = subprocess.Popen(
            [sys.executable, "-m", "pytest", *args],
            cwd=root, stdin=subprocess.DEVNULL, stdout=oh, stderr=eh,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        )
    print(f"DETACHED_PYTEST_PID={p.pid}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
