from src.core.saas_entitlements import SaaSEntitlements
from src.core.usage_billing import UsageBilling


def test_default_free_plan(tmp_path):
    e = SaaSEntitlements(tmp_path / "e.sqlite3")
    assert e.subscription("t1", "w1")["plan"] == "free"
    assert e.check("t1", "w1", "runtime")["allowed"] is True
    assert e.check("t1", "w1", "lms")["allowed"] is False


def test_subscription_syncs_billing(tmp_path):
    b = UsageBilling(tmp_path / "b.sqlite3")
    e = SaaSEntitlements(tmp_path / "e.sqlite3", usage_billing=b)
    result = e.set_subscription("t1", "w1", "business")
    assert result["plan"] == "business"
    assert b.invoice_preview("t1", "w1")["plan"] == "business"
    assert e.check("t1", "w1", "security")["allowed"] is True


def test_override_and_suspended(tmp_path):
    e = SaaSEntitlements(tmp_path / "e.sqlite3")
    e.set_override("t1", "w1", "lms", True)
    assert e.check("t1", "w1", "lms")["allowed"] is True
    e.set_subscription("t1", "w1", "free", status="suspended")
    assert e.check("t1", "w1", "lms")["allowed"] is False


def test_tenant_workspace_isolation(tmp_path):
    e = SaaSEntitlements(tmp_path / "e.sqlite3")
    e.set_subscription("t1", "w1", "enterprise")
    assert e.subscription("t2", "w1")["plan"] == "free"
    assert e.subscription("t1", "w2")["plan"] == "free"
    assert e.check("t2", "w1", "api")["allowed"] is False


def test_validation_and_health(tmp_path):
    e = SaaSEntitlements(tmp_path / "e.sqlite3")
    try:
        e.set_subscription("t1", "w1", "invalid")
        assert False
    except ValueError as exc:
        assert str(exc) == "invalid_plan"
    try:
        e.set_subscription("t1", "w1", "free", status="bad")
        assert False
    except ValueError as exc:
        assert str(exc) == "invalid_subscription_status"
    assert e.health()["credentials_exposed"] is False
