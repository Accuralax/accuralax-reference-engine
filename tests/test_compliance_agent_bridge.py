from src.core.compliance_risk_engine import ComplianceRiskEngine
from src.core.compliance_intelligence import ComplianceIntelligence
from src.core.compliance_agent_bridge import ComplianceAgentBridge
from src.core.human_approval import HumanApprovalGateway
from src.core.event_bus import EventBus


def build(tmp_path):
    engine = ComplianceRiskEngine(str(tmp_path / "risk.sqlite3"))
    intelligence = ComplianceIntelligence(engine)
    approvals = HumanApprovalGateway(str(tmp_path / "approval.sqlite3"))
    return engine, ComplianceAgentBridge(intelligence, engine, approvals), approvals


def test_high_risk_remediation_is_approval_gated(tmp_path):
    engine, bridge, approvals = build(tmp_path)
    bridge.events = EventBus(str(tmp_path / "events.sqlite3"))
    risk = engine.assess_risk("t1", "w1", "Missing control", 5, 5)
    result = bridge.assess("t1", "w1", "agent")
    assert result["requires_human_approval"] is True
    events = bridge.events.history("t1", "w1", event_type="compliance.agent.proposal_created")
    assert len(events) == 1
    assert len(result["proposals"]) == 1
    proposal = result["proposals"][0]
    blocked = bridge.execute("t1", "w1", proposal["proposal_id"], "agent")
    assert blocked["status"] == "blocked"
    approvals.approve("t1", "w1", proposal["approval"]["approval_id"], "reviewer")
    executed = bridge.execute("t1", "w1", proposal["proposal_id"], "reviewer")
    assert executed["status"] == "executed"
    assert executed["action"]["status"] == "in_progress"


def test_scope_isolation(tmp_path):
    engine, bridge, _ = build(tmp_path)
    engine.assess_risk("t1", "w1", "Risk", 5, 5)
    result = bridge.assess("t1", "w2", "agent")
    assert result["proposals"] == []
