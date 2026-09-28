from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"apex_parallel"/"integration_certification.json"
TESTS=[
    "tests/test_apex_integration_convergence.py",
    "tests/test_external_adapters.py",
    "tests/test_integration_router.py",
    "tests/test_audited_integration_router.py",
    "tests/test_durable_ledger.py",
    "tests/test_credential_isolation.py",
    "tests/test_enterprise_integration_layer.py",
]

def main():
    env=os.environ.copy()
    env.pop("HUBSPOT_ACCESS_TOKEN",None)
    env.pop("MAKE_API_TOKEN",None)
    env.pop("MAKE_WEBHOOK_URL",None)
    cmd=[sys.executable,"-m","pytest","-q","--disable-warnings",*TESTS]
    p=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    report={"timestamp":datetime.now(timezone.utc).isoformat(),
            "credential_gate":"untouched",
            "live_credentials_removed_from_test_environment":True,
            "returncode":p.returncode,
            "passed":p.returncode==0,
            "tests":TESTS,
            "stdout_tail":p.stdout[-12000:],
            "stderr_tail":p.stderr[-4000:]}
    OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return p.returncode

if __name__=="__main__":
    raise SystemExit(main())
