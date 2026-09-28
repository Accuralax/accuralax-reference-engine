from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "apex_parallel"

A20 = json.loads((DATA / "apex20_full_regression_certification.json").read_text(encoding="utf-8"))
STAGES = json.loads((DATA / "apex_stage_certification.json").read_text(encoding="utf-8"))
OFFLINE_PATH = DATA / "apex_offline_production_certification.json"
OFFLINE = json.loads(OFFLINE_PATH.read_text(encoding="utf-8")) if OFFLINE_PATH.exists() else {}

A20_OK = A20.get("status") == "CERTIFIED" and A20.get("tests_passed") == 657 and A20.get("tests_failed") == 0 and A20.get("tests_skipped") == 0
STAGE_ROWS = {x["stage"]: x for x in STAGES.get("stages", [])}
OFFLINE_OK = OFFLINE.get("status") == "CERTIFIED_OFFLINE"

# A29/A30 can be certified offline for fail-closed behavior, but live activation remains mandatory.
LIVE_REQUIRED = ["APEX-A29", "APEX-A30"]
LIVE_BLOCK = [stage for stage in LIVE_REQUIRED if not STAGE_ROWS.get(stage, {}).get("offline", False)]

result = {
    "pipeline": "APEX-A19→A33→Ω",
    "build_state": "COMPLETE",
    "regression": "CERTIFIED_657" if A20_OK else "BLOCKED",
    "authoritative_regression_sha256": A20.get("sha256"),
    "offline_stage_verification": "COMPLETE" if OFFLINE_OK else "BLOCKED",
    "offline_certification": "CERTIFIED_OFFLINE" if OFFLINE_OK else "MISSING_OR_FAILED",
    "live_external_certification": "BLOCKED_PENDING_LIVE_PROVIDER_EVIDENCE",
    "release_allowed": False,
    "blocking_stages": LIVE_REQUIRED if OFFLINE_OK else LIVE_REQUIRED + ["APEX-A30_OFFLINE"],
    "reason": "Live Supabase/Make/HubSpot provider evidence and production authentication are still required; offline evidence is not a substitute.",
    "fail_closed": True,
}
result["sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
(DATA / "apex_final_release_gate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
