import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from integrations.convergence import IntegrationConvergence
from integrations.credentials import CredentialProvider
from integrations.provider_health import ProviderHealthRegistry

def test_convergence_wires_credential_state_and_health(monkeypatch):
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("MAKE_API_TOKEN", raising=False)
    monkeypatch.delenv("MAKE_WEBHOOK_URL", raising=False)
    c = IntegrationConvergence(credentials=CredentialProvider())
    assert c.credential_states.check("hubspot").state.value == "missing"
    assert c.credential_states.check("make").state.value == "missing"
    assert c.provider_health.inspect("hubspot").probe_status == "adapter_missing"

def test_health_public_view_contains_no_secret(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "sentinel-secret")
    h = ProviderHealthRegistry(adapters={"hubspot": object()}).inspect("hubspot").public()
    rendered = repr(h).lower()
    assert h["configured"] is True
    assert "sentinel-secret" not in rendered
    assert "access_token" not in rendered
