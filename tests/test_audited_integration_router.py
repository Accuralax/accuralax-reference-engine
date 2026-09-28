import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from integrations.audited_router import AuditedIntegrationRouter
from integrations.adapters.base import MockBusinessAdapter
from core.business_gateway import BusinessCapabilityGateway

def test_audited_router_denies_without_approval():
    a=MockBusinessAdapter("hubspot", {"upsert_contact"})
    r=AuditedIntegrationRouter(BusinessCapabilityGateway(), {"hubspot": a})
    out=r.execute("hubspot","upsert_contact",{"x":1},approved=False,idempotency_key="k1")
    assert out["authorized"] is False
    assert not a.calls

def test_audited_router_executes_authorized_mock():
    a=MockBusinessAdapter("hubspot", {"upsert_contact"})
    r=AuditedIntegrationRouter(BusinessCapabilityGateway(), {"hubspot": a})
    out=r.execute("hubspot","upsert_contact",{"x":1},approved=True,idempotency_key="k2")
    assert out["authorized"] is True
    assert out["status"] in {"completed","success"}
    assert a.calls == [("upsert_contact", {"x":1})]
