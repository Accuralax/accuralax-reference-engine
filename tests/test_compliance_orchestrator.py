from src.core.compliance_orchestrator import ComplianceOrchestrator
from src.core.compliance_risk_engine import ComplianceRiskEngine
from src.core.compliance_intelligence import ComplianceIntelligence
from src.core.compliance_report_agent import ComplianceReportAgent
from src.core.compliance_agent_bridge import ComplianceAgentBridge
from src.core.human_approval import HumanApprovalGateway
from src.core.event_bus import EventBus


def build(tmp_path):
    risk = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    intelligence = ComplianceIntelligence(risk)
    report = ComplianceReportAgent(intelligence, str(tmp_path / "reports.sqlite3"))
    approvals = HumanApprovalGateway(str(tmp_path / "approvals.sqlite3"))
    bridge = ComplianceAgentBridge(intelligence, risk, approvals)
    bridge.events = EventBus(str(tmp_path / "bridge-events.sqlite3"))
    events = EventBus(str(tmp_path / "events.sqlite3"))
    return risk, ComplianceOrchestrator(report, bridge, events, str(tmp_path / "orchestrator.sqlite3")), events


def test_end_to_end_approval_gate_and_execution(tmp_path):
    risk, orchestrator, events = build(tmp_path)
    risk.assess_risk("t1", "w1", "Missing control", 5, 5)
    result = orchestrator.assess("t1", "w1", "system")
    assert result["status"] == "awaiting_approval"
    assert len(result["proposals"]) == 1
    proposal = result["proposals"][0]
    blocked = orchestrator.execute("t1", "w1", result["run_id"], "worker")
    assert blocked["status"] == "blocked_pending_approval"
    approved = orchestrator.approve_proposal("t1", "w1", result["run_id"], proposal["proposal_id"], True, "reviewer")
    assert approved["status"] == "approved"
    executed = orchestrator.execute("t1", "w1", result["run_id"], "reviewer")
    assert executed["status"] == "completed"
    assert events.history("t1", "w1", entity_id=result["run_id"])


def test_run_is_tenant_workspace_isolated(tmp_path):
    risk, orchestrator, _ = build(tmp_path)
    risk.assess_risk("t1", "w1", "Risk", 5, 5)
    result = orchestrator.assess("t1", "w1")
    assert orchestrator.get("t2", "w1", result["run_id"]) is None
    assert orchestrator.get("t1", "w2", result["run_id"]) is None


def test_process_event_is_idempotent(tmp_path):
    risk, orchestrator, events = build(tmp_path)
    risk.assess_risk("t1", "w1", "Risk", 5, 5)
    event = type("Event", (), {"event_type":"compliance.assessment.requested", "event_id":"evt-1", "tenant_id":"t1", "workspace_id":"w1", "actor_id":"system", "payload":{}})()
    first = orchestrator.process_event(event)
    second = orchestrator.process_event(event)
    assert first["run_id"] == second["run_id"]
    assert second["status"] == "already_processed"
    assert orchestrator.get("t1", "w1", first["run_id"]) is not None


def test_assessment_event_is_idempotent_by_run(tmp_path):
    risk, orchestrator, events = build(tmp_path)
    risk.assess_risk("t1", "w1", "Risk", 5, 5)
    result = orchestrator.assess("t1", "w1")
    before = len(events.history("t1", "w1", entity_id=result["run_id"]))
    assert before == 1
    assert orchestrator.get("t1", "w1", result["run_id"]) is not None
    after = len(events.history("t1", "w1", entity_id=result["run_id"]))
    assert after == before
