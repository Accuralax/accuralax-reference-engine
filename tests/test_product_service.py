from src.core.product_service import ProductService


def test_product_service_health():
    ps = ProductService()
    assert ps.health()["status"] == "ok"
    assert ps.health()["credentials_exposed"] is False


def test_activation_and_pricing_require_approval():
    ps = ProductService()
    offering = ps.create_offering("Managed Cybersecurity", "service")
    blocked = ps.activate(offering["offering_id"])
    assert blocked["allowed"] is False
    active = ps.activate(offering["offering_id"], approved=True)
    assert active["allowed"] is True
    pricing = ps.set_pricing(offering["offering_id"], 2500)
    assert pricing["allowed"] is False
    priced = ps.set_pricing(offering["offering_id"], 2500, approved=True)
    assert priced["allowed"] is True
    assert priced["pricing"]["currency"] == "ZAR"


def test_release_subscription_and_service_request():
    ps = ProductService()
    offering = ps.create_offering("Wolas.ai", "product")
    release = ps.create_release(offering["offering_id"], "1.0.0")
    subscription = ps.create_subscription("CUS-1", offering["offering_id"])
    request = ps.create_service_request("CUS-1", offering["offering_id"], "Onboarding")
    assert release["status"] == "planned"
    assert subscription["status"] == "trial"
    assert request["status"] == "open"
