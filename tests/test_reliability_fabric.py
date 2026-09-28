from src.core.reliability_fabric import ReliabilityFabric


def test_detect_diagnose_and_safe_repair():
    fabric = ReliabilityFabric()
    fabric.report_health("rag", "degraded", "stale index", api_key="never-store")
    diagnosis = fabric.diagnose("rag")
    assert diagnosis["status"] == "issue_detected"
    plan = fabric.propose_repair("rag", "stale index", "reindex", risk="medium")
    fabric.register_repair_handler(plan.repair_id, lambda: {"reindexed": True})
    result = fabric.execute_repair(plan.repair_id)
    assert result["allowed"]
    assert result["verified"] is False
    verified = fabric.verify_repair(plan.repair_id, lambda: True)
    assert verified["verified"]


def test_high_risk_repair_requires_approval():
    fabric = ReliabilityFabric()
    plan = fabric.propose_repair("security", "policy drift", "restore", risk="high")
    fabric.register_repair_handler(plan.repair_id, lambda: {"restored": True})
    blocked = fabric.execute_repair(plan.repair_id)
    assert blocked["reason"] == "human_approval_required"
    approved = fabric.execute_repair(plan.repair_id, approved=True)
    assert approved["allowed"]


def test_health_is_bounded_and_safe():
    fabric = ReliabilityFabric()
    health = fabric.health()
    assert health["status"] == "ok"
    assert health["max_repair_iterations"] == 3
    assert health["credentials_exposed"] is False
