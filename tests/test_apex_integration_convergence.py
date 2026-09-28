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


def test_retry_policy_exponential_and_nonretryable():
    from integrations.retry_policy import RetryPolicy
    p=RetryPolicy(max_attempts=4,base_delay_seconds=2,max_delay_seconds=5)
    assert p.delay(1)==2
    assert p.delay(2)==4
    assert p.delay(3)==5
    assert p.should_retry(1,retryable=True)
    assert not p.should_retry(4,retryable=True)
    assert not p.should_retry(1,retryable=False)


def test_reconciliation_worker_replays_failed_job(tmp_path):
    from integrations.reconciliation_worker import ReconciliationWorker
    calls=[]
    class Flaky:
        def execute(self, action, payload):
            calls.append(1)
            if len(calls)==1: raise RuntimeError("temporary timeout")
            return {"ok":True}
    x, _, _ = build(tmp_path, hub=Flaky(), max_attempts=3)
    first=x.dispatch("t","w","crm.contact.search",{"email":"worker@example.com"},idempotency_key="worker-1")
    assert first["status"]=="failed"
    result=ReconciliationWorker(x.durable).run_once("t","w")
    assert result.scanned==1 and result.completed==1
    assert x.durable.reconciliation_queue("t","w")==[]


def test_reconciliation_worker_is_bounded(tmp_path):
    from integrations.reconciliation_worker import ReconciliationWorker
    worker=ReconciliationWorker(build(tmp_path)[0].durable)
    result=worker.run_until_empty("t","w",max_cycles=2)
    assert result.scanned==0 and result.replayed==0


def test_integration_observability_reconciliation_metrics(tmp_path):
    from core.observability import Observability
    from integrations.integration_observability import IntegrationObservability
    from integrations.reconcile import ReconcileBatch
    store=Observability(str(tmp_path/"obs.sqlite3"))
    obs=IntegrationObservability(store)
    batch=ReconcileBatch(3,3,2,1,0,0,({"attempts":2},{"attempts":1},{"attempts":1}))
    obs.record_queue_depth("t","w",3)
    obs.record_reconciliation("t","w",batch)
    snap=obs.snapshot("t","w")
    assert snap["metric_totals"]["integration.reconciliation.queue_depth"]==3
    assert snap["metric_totals"]["integration.reconciliation.completed"]==2
    assert snap["metric_totals"]["integration.reconciliation.failed"]==1
    assert snap["metric_totals"]["integration.retry.attempts"]==4


def test_provider_health_contract_probe_hides_credentials(monkeypatch):
    from integrations.provider_health import ProviderHealthProbe
    from integrations.credentials import CredentialProvider
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN","top-secret")
    health=ProviderHealthProbe(CredentialProvider()).probe("hubspot",object(),("crm.contact.search",))
    assert health.credential_state=="available"
    assert health.contract_ok is True
    assert "top-secret" not in str(health.public())
