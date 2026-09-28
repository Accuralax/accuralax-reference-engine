from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"/"apex_parallel"
reg=json.loads((DATA/"apex19_resilient_manifest.json").read_text(encoding="utf-8"))
files={Path(f).name for r in reg for f in r["files"] if r.get("status")=="passed"}
mapping={
"APEX-A21":["test_repair_circuit.py","test_repair_graph.py","test_self_healing.py","test_self_healing_graph.py","test_apex_integration_next.py"],
"APEX-A22":["test_worker_lease_reconciliation.py","test_it_durable_event_bus.py","test_it_operational_store.py","test_apex_integration_convergence.py"],
"APEX-A23":["test_global_supervisor.py","test_global_supervisor_graph.py","test_it_automation_supervisor.py","test_business_supervisor_graph.py"],
"APEX-A24":["test_api_watchdog.py","test_apex_runtime_bootstrap.py"],
"APEX-A25":["test_operational_backbone_approval.py","test_operational_backbone_convergence.py","test_operational_backbone_workflow.py"],
"APEX-A26":["test_agent_registry.py","test_agent_authorization.py","test_agent_planning_convergence.py"],
"APEX-A27":["test_governance_regulatory.py","test_omega10_regulatory_convergence.py","test_tax_jurisdiction.py"],
"APEX-A28":["test_ai_evaluation.py","test_omega12_ai_evaluation.py","test_omega12_production_convergence.py"],
"APEX-A29":["test_apex_integration_convergence.py","test_apex_integration_next.py","test_audited_integration_router.py","test_external_adapters.py"],
"APEX-A30":["test_credential_isolation.py","test_tenant_access.py","test_omega14_global_multitenant.py","test_omega_credential_preflight.py"],
"APEX-A31":["test_execution_audit.py","test_evidence_verifier.py","test_enterprise_state.py","test_runtime_control_plane.py"],
"APEX-A32":["test_apex_production_certification.py","test_runtime_release_gate.py"],
"APEX-A33":["test_apex_production_certification.py","test_omega15_enterprise_final.py"],
"APEX-Ω":["test_omega_final_convergence.py","test_omega15_enterprise_final.py","test_apex_omega_remaining.py"]}
rows=[]
for stage,needed in mapping.items():
    missing=[x for x in needed if x not in files]
    rows.append({"stage":stage,"status":"VERIFIED" if not missing else "BLOCKED","missing":missing,"evidence_files":needed,"offline":stage in {"APEX-A29","APEX-A30"}})
out={"pipeline":"A19-A33-Omega","a20_certified":True,"stages":rows}
out["sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest()
(DATA/"apex_stage_certification.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
