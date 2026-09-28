import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.business_gateway import BusinessCapabilityGateway
from core.enterprise_integration_layer import EnterpriseIntegrationLayer
from integrations.adapters.base import MockBusinessAdapter
from integrations.convergence import IntegrationConvergence

def build(tmp_path, hub=None, make=None, max_attempts=2):
    hub = hub or MockBusinessAdapter("hubspot", {"search_contact","create_contact"})
    make = make or MockBusinessAdapter("make", {"trigger_webhook","read_scenario_status"})
    durable = EnterpriseIntegrationLayer(db_path=str(tmp_path/"jobs.sqlite3"), max_attempts=max_attempts)
    return IntegrationConvergence(BusinessCapabilityGateway(), {"hubspot":hub,"make":make}, durable), hub, make

def test_a1_canonical_hubspot_mapping(tmp_path):
    x, hub, _ = build(tmp_path)
    r=x.dispatch("t","w","crm.contact.search",{"email":"a@example.com"})
    assert r["status"]=="completed"
    assert hub.calls==[("search_contact",{"email":"a@example.com"})]

def test_a2_make_webhook_boundary(tmp_path):
    x, _, make = build(tmp_path)
    r=x.dispatch("t","w","automation.webhook.trigger",{"reference_id":"ALX-TEST"},
                 approved=True,idempotency_key="mk-1")
    assert r["status"]=="completed"
    assert make.calls[0][0]=="trigger_webhook"

def test_denied_capability_never_executes(tmp_path):
    x, hub, _ = build(tmp_path)
    r=x.dispatch("t","w","crm.contact.delete",{"id":"1"})
    assert r["status"]=="denied"
    assert not hub.calls

def test_credential_missing_is_durable_failure(tmp_path):
    class Missing:
        def execute(self, action, payload):
            raise RuntimeError("hubspot_credentials_not_configured")
    x, _, _ = build(tmp_path, hub=Missing())
    r=x.dispatch("t","w","crm.contact.search",{"email":"a@example.com"})
    assert r["status"]=="failed"
    assert r["reason"]=="hubspot_credentials_not_configured"

def test_idempotency_and_reconciliation(tmp_path):
    calls=[]
    class Flaky:
        def execute(self, action, payload):
            calls.append(1)
            if len(calls)==1: raise RuntimeError("temporary")
            return {"ok":True}
    x, _, make = build(tmp_path, hub=Flaky(), max_attempts=2)
    first=x.dispatch("t","w","crm.contact.search",{"email":"a@example.com"},idempotency_key="r-1")
    assert first["status"]=="failed"
    q=x.durable.reconciliation_queue("t","w")
    assert len(q)==1
    second=x.durable.reconcile("t","w",replay=True)
    assert second["results"][0]["status"]=="completed"
    again=x.dispatch("t","w","crm.contact.search",{"email":"different@example.com"},idempotency_key="r-1")
    assert again["job_id"]==first["job_id"]
    assert len(calls)==2

def test_contract_matrix_is_provider_neutral():
    from integrations.contract_matrix import matrix
    rows=matrix()
    assert rows and any(r["capability"]=="crm.contact.search" for r in rows)


def test_credential_state_matrix_never_exposes_secret(tmp_path, monkeypatch):
    from integrations.credential_state import CredentialState, CredentialStateMatrix
    from integrations.credentials import CredentialProvider
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN","secret-not-for-agents")
    status=CredentialStateMatrix(CredentialProvider()).check("hubspot")
    assert status.state == CredentialState.AVAILABLE
    assert "secret-not-for-agents" not in str(status)


def test_response_normalization_retryability():
    from integrations.response_normalizer import normalize
    ok=normalize("make", {"ok":True,"execution_id":"m1"})
    retry=normalize("hubspot", {"ok":False,"error":"temporary timeout"})
    assert ok.status=="completed"
    assert retry.retryable is True
    assert retry.error_code=="temporary_timeout"
