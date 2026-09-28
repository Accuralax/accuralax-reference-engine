from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(*args: str) -> str:
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return (p.stdout + p.stderr).strip()

def main() -> int:
    print("GIT_ROOT=" + run("git", "rev-parse", "--show-toplevel"))
    print("GIT_BRANCH=" + run("git", "branch", "--show-current"))
    print("GIT_STATUS_BEGIN")
    print(run("git", "status", "--short"))
    print("GIT_STATUS_END")
    print("GIT_REMOTES_BEGIN")
    print(run("git", "remote", "-v"))
    print("GIT_REMOTES_END")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
