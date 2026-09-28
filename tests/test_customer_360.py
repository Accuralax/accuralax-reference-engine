from src.core.customer_360 import Customer360

def test_customer_360_persists_relationships_events_and_consents(tmp_path):
    e = Customer360(str(tmp_path / "360.sqlite3"))
    e.add_relationship("t1","w1","CLI-1","account_manager","Mpumelelo")
    e.record_event("t1","w1","CLI-1","whatsapp","message","Requested proposal")
    e.set_consent("t1","w1","CLI-1","marketing",True,"whatsapp")
    e.create_opportunity("t1","w1","CLI-1","Website project","qualified",1000,"ZAR")
    fresh = Customer360(str(tmp_path / "360.sqlite3"))
    view = fresh.customer_360("t1","w1","CLI-1")
    assert len(view["relationships"]) == 1
    assert len(view["timeline"]) == 1
    assert view["consents"][0]["granted"] is True
    assert view["opportunities"][0]["currency"] == "ZAR"

def test_customer_360_is_tenant_scoped(tmp_path):
    e = Customer360(str(tmp_path / "360.sqlite3"))
    e.record_event("t1","w1","CLI-1","web","lead","hello")
    assert e.timeline("t2","w1","CLI-1") == []
    assert e.handoff_allowed("t2","w1","CLI-1","marketing") is False

def test_customer_360_requires_client_id(tmp_path):
    e = Customer360(str(tmp_path / "360.sqlite3"))
    try:
        e.record_event("t1","w1","","web","lead","hello")
        assert False
    except ValueError as exc:
        assert str(exc) == "client_id_required"
    assert e.health()["status"] == "ok"
