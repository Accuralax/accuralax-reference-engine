import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from core.enterprise_integration_layer import EnterpriseIntegrationLayer
from core.observability import Observability
from integrations.integration_observability import IntegrationObservability
from integrations.provider_health import ProviderHealthRegistry
from integrations.reconcile import IntegrationReconciler
from integrations.retry_policy import RetryPolicy

def test_retry_policy_is_bounded():
    p=RetryPolicy(max_attempts=3,base_delay_seconds=2)
    assert p.should_retry(1,retryable=True)
    assert not p.should_retry(3,retryable=True)
    assert not p.should_retry(1,retryable=False)
    assert p.delay(3)==8

def test_reconciler_replays_failed(tmp_path):
    x=EnterpriseIntegrationLayer(db_path=str(tmp_path/"jobs.sqlite3"),max_attempts=3)
    calls=[]
    def flaky(a,p,j):
        calls.append(1)
        if len(calls)==1: raise RuntimeError("temporary timeout")
        return {"ok":True}
    x.register_connector("hubspot",flaky)
    first=x.dispatch("t","w","hubspot","sync",{"x":1},idempotency_key="r1")
    assert first["status"]=="failed"
    sleeps=[]
    b=IntegrationReconciler(x,RetryPolicy(max_attempts=3,base_delay_seconds=.25),sleep_fn=sleeps.append).run_once("t","w")
    assert b.completed==1 and calls==[1,1] and sleeps==[.25]

def test_dead_letter_is_not_auto_replayed(tmp_path):
    x=EnterpriseIntegrationLayer(db_path=str(tmp_path/"jobs.sqlite3"),max_attempts=1)
    x.register_connector("bad",lambda a,p,j: (_ for _ in ()).throw(RuntimeError("permanent")))
    first=x.dispatch("t","w","bad","sync")
    assert first["status"]=="dead_letter"
    b=IntegrationReconciler(x).run_once("t","w")
    assert b.skipped==1

def test_provider_health_is_dry_run(monkeypatch):
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN",raising=False)
    s=ProviderHealthRegistry(adapters={"hubspot":object()}).inspect("hubspot")
    assert s.probe_status=="credential_missing" and not s.configured
    assert "crm.contact.search" in s.capabilities

def test_integration_observability_is_scoped(tmp_path):
    f=IntegrationObservability(Observability(str(tmp_path/"obs.sqlite3")))
    f.record_job({"tenant_id":"t1","workspace_id":"w1","job_id":"j1","connector":"hubspot","action":"search","status":"failed","attempts":1,"trace_id":"tr1","correlation_id":"co1"})
    assert f.snapshot("t1","w1")["metric_totals"]["integration.jobs"]==1
    assert f.snapshot("t1","w1")["metric_totals"]["integration.failures"]==1
    assert f.snapshot("t2","w2")["metric_totals"]=={}
