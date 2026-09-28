import pytest

from src.core.agentic_workspace import AgenticWorkspace
from src.core.runtime_contract import RuntimeExecutionContract


def test_contract_round_trip_and_safe_tool_call():
    contract = RuntimeExecutionContract(request="create a business plan")
    contract.add_tool_call({"name": "crm.lookup", "credentials": "secret"})
    restored = RuntimeExecutionContract.from_dict(contract.to_dict())

    assert restored.request == contract.request
    assert restored.credentials_exposed is False
    assert restored.tool_calls[0] == {"name": "crm.lookup"}


def test_contract_rejects_invalid_status():
    with pytest.raises(ValueError):
        RuntimeExecutionContract(status="not_a_status")


def test_high_risk_contract_requires_approval():
    contract = RuntimeExecutionContract(
        request="execute a high risk operation",
        status="awaiting_approval",
        risk_level="high",
        approval_state="pending",
    )
    contract.approve()
    assert contract.status == "running"
    assert contract.approval_state == "approved"


def test_workspace_returns_canonical_runtime_contract():
    result = AgenticWorkspace().run("I need help with cybersecurity")
    contract = result["runtime_contract"]

    assert result["reference_id"] == contract["reference_id"]
    assert result["request_id"] == contract["request_id"]
    assert result["trace_id"] == contract["trace_id"]
    assert contract["credentials_exposed"] is False
    assert "policy_decisions" in contract
