from datetime import datetime, timezone

import pytest

from src.core.enterprise_entity_model import EnterpriseEntityModel


def payload(key, value):
    return {key: value, "created_at": datetime.now(timezone.utc).isoformat()}


def test_upsert_get_and_update(tmp_path):
    model = EnterpriseEntityModel(tmp_path / "entities.sqlite3")
    first = model.upsert("t1", "w1", "person", payload("person_id", "p1"))
    assert first["status"] == "created"
    second = model.upsert("t1", "w1", "person", {"person_id": "p1", "created_at": first["entity_id"], "name": "Updated"})
    assert second["status"] == "updated"
    found = model.get("t1", "w1", first["entity_id"])
    assert found["payload"]["name"] == "Updated"


def test_tenant_isolation(tmp_path):
    model = EnterpriseEntityModel(tmp_path / "entities.sqlite3")
    item = model.upsert("t1", "w1", "person", payload("person_id", "p1"))
    assert model.get("t2", "w1", item["entity_id"]) is None


def test_registry_relationships_and_scope(tmp_path):
    model = EnterpriseEntityModel(tmp_path / "entities.sqlite3")
    person = model.upsert("t1", "w1", "person", payload("person_id", "p1"))
    org = model.upsert("t1", "w1", "organisation", payload("organisation_id", "o1"))
    link = model.link("t1", "w1", person["entity_id"], org["entity_id"], "member_of")
    assert link["status"] == "created"
    assert model.links("t1", "w1", person["entity_id"])[0]["target_entity_id"] == org["entity_id"]
    with pytest.raises(ValueError, match="entity_not_found_in_scope"):
        model.link("t2", "w1", person["entity_id"], org["entity_id"], "member_of")


def test_invalid_relationship_rejected(tmp_path):
    model = EnterpriseEntityModel(tmp_path / "entities.sqlite3")
    person = model.upsert("t1", "w1", "person", payload("person_id", "p1"))
    risk = model.upsert("t1", "w1", "risk", payload("risk_id", "r1"))
    with pytest.raises(ValueError, match="relationship_not_allowed_by_registry"):
        model.link("t1", "w1", person["entity_id"], risk["entity_id"], "owns")
