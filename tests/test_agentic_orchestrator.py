from src.core.agentic_orchestrator import AgenticOrchestrator


def test_orchestration_checkpoint_and_completion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    orch = AgenticOrchestrator()
    state = orch.start("analyse cybersecurity controls", "CFS-ORCH-1")
    state = orch.delegate(state, "cybersecurity_triage_agent", "cybersecurity")
    assert state.status == "executing"
    result = orch.complete(state)
    assert result["status"] == "completed"
    assert result["trace"]["credentials_exposed"] is False
    assert orch.resume("CFS-ORCH-1")["resumable"]


def test_high_risk_gate_requires_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    orch = AgenticOrchestrator()
    state = orch.start("capture payment")
    state = orch.gate(state, "payment.capture", high_risk=True, external_side_effect=True)
    assert state.status == "awaiting_approval"
    assert state.approval_required


def test_approved_high_risk_gate_can_proceed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    orch = AgenticOrchestrator()
    state = orch.start("capture payment")
    state = orch.gate(
        state, "payment.capture", high_risk=True, external_side_effect=True,
        approved=True, policy_check_passed=True
    )
    assert state.status == "verified"
