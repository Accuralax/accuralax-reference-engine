from src.integrations import HubSpotAdapter, MakeAdapter

def test_hubspot_contract_with_injected_transport():
    seen = {}
    def transport(action, payload, token):
        seen.update(action=action, payload=payload, token=token)
        return {"ok": True}
    a = HubSpotAdapter(transport=transport, token="test-token")
    result = a.execute("upsert_contact", {"email": "test@example.invalid"})
    assert result["connector"] == "hubspot"
    assert seen["token"] == "test-token"

def test_make_contract_with_injected_transport():
    seen = {}
    def transport(action, payload, token, webhook):
        seen.update(action=action, payload=payload, token=token, webhook=webhook)
        return {"queued": True}
    a = MakeAdapter(transport=transport, token="test-token", webhook="https://example.invalid")
    result = a.execute("trigger", {"reference_id": "ALX-TEST"})
    assert result["connector"] == "make"
    assert seen["webhook"] == "https://example.invalid"

def test_external_adapters_fail_closed_without_transport_or_credentials(monkeypatch):
    for key in ("HUBSPOT_ACCESS_TOKEN", "MAKE_API_TOKEN", "MAKE_WEBHOOK_URL"):
        monkeypatch.delenv(key, raising=False)
    try:
        HubSpotAdapter().execute("x", {})
        assert False
    except RuntimeError as exc:
        assert str(exc) == "hubspot_credentials_not_configured"
    try:
        MakeAdapter().execute("x", {})
        assert False
    except RuntimeError as exc:
        assert str(exc) == "make_credentials_not_configured"
