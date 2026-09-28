from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"/"apex_parallel"
p=DATA/"apex20_current_manifest.json"; rows=json.loads(p.read_text(encoding="utf-8"))
rows=sorted(rows,key=lambda x:int(x["batch"]))
files=[f for r in rows for f in r["files"]]
tests=sum(int(r.get("tests_passed",0)) for r in rows)
failures=sum(int(r.get("tests_failed",0)) for r in rows); skipped=sum(int(r.get("tests_skipped",0)) for r in rows)
checks={
"30_batches":len(rows)==30,
"175_unique_test_files":len(files)==175 and len(set(files))==175,
"659_tests_passed":tests==659,
"zero_failures":failures==0,
"zero_skipped":skipped==0,
"all_batches_passed":all(r.get("status")=="passed" for r in rows)}
evidence={"stage":"APEX-A20","status":"CERTIFIED" if all(checks.values()) else "BLOCKED","checks":checks,"batches":len(rows),"test_files":len(set(files)),"tests_passed":tests,"tests_failed":failures,"tests_skipped":skipped}
raw=json.dumps(evidence,sort_keys=True).encode(); evidence["sha256"]=hashlib.sha256(raw).hexdigest()
(DATA/"apex20_full_regression_certification.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
print(json.dumps(evidence,indent=2))
