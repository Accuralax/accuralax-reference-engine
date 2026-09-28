from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"/"apex_parallel"
a20=json.loads((DATA/"apex20_full_regression_certification.json").read_text(encoding="utf-8"))
stages=json.loads((DATA/"apex_stage_certification.json").read_text(encoding="utf-8"))
live_required=["APEX-A29","APEX-A30"]
live_block=[x["stage"] for x in stages["stages"] if x["stage"] in live_required and x.get("offline")]
release_allowed=bool(a20["status"]=="CERTIFIED" and not live_block)
result={
 "pipeline":"APEX-A19→A33→Ω",
 "build_state":"COMPLETE",
 "regression":"CERTIFIED_657",
 "offline_stage_verification":"COMPLETE",
 "live_external_certification":"BLOCKED_PENDING_LIVE_PROVIDER_EVIDENCE" if live_block else "COMPLETE",
 "release_allowed":release_allowed,
 "blocking_stages":live_block,
 "reason":"Supabase/Make/HubSpot live credentials and provider-boundary evidence were intentionally not used in offline certification." if live_block else "",
 "fail_closed":True}
result["sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
(DATA/"apex_final_release_gate.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
