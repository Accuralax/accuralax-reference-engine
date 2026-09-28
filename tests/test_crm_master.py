from src.core.crm_master import CRMIdentityEngine

def test_create_search_and_duplicate(tmp_path):
    e = CRMIdentityEngine(str(tmp_path / "crm.sqlite3"))
    a = e.create_client("t1","w1","organisation","AccuraLax Solutions Group","info@example.com","+27821234567","ZA",
                        registration_number="2026/123/07")
    assert a["created"] is True
    assert e.search("t1","w1","accuralax")[0]["client_id"] == a["client_id"]
    dup = e.create_client("t1","w1","organisation","Same Company","INFO@EXAMPLE.COM","+27 82 123 4567","ZA")
    assert dup["duplicate"] is True
    assert a["client_id"] in dup["existing_client_ids"]

def test_scope_and_identity_link(tmp_path):
    e = CRMIdentityEngine(str(tmp_path / "crm.sqlite3"))
    a = e.create_client("t1","w1","person","Jane Doe","jane@example.com")
    assert e.search("t2","w1","jane") == []
    linked = e.link_identity("t1","w1",a["client_id"],"ORG-ABC","tester")
    assert linked["identity_id"] == "ORG-ABC"
    assert len(linked["stable_key"]) == 20

def test_invalid_type_and_health(tmp_path):
    e = CRMIdentityEngine(str(tmp_path / "crm.sqlite3"))
    try:
        e.create_client("t1","w1","company","X")
        assert False
    except ValueError as exc:
        assert str(exc) == "invalid_entity_type"
    assert e.health()["status"] == "ok"
