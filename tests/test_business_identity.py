from src.core.business_identity import BusinessIdentityEngine

def test_address_schema_and_validation(tmp_path):
    e = BusinessIdentityEngine(str(tmp_path / "identity.sqlite3"))
    schema = e.address_schema("ZA")
    assert "province" in schema["required_fields"]
    good = e.validate_address("ZA", {
        "address_line1":"1 Main Road","city":"Brakpan","province":"Gauteng","postal_code":"1540"
    })
    assert good["valid"] is True
    bad = e.validate_address("ZA", {
        "address_line1":"1 Main Road","city":"Brakpan","province":"Gauteng","postal_code":"ABC"
    })
    assert bad["valid"] is False

def test_identity_create_and_scope(tmp_path):
    e = BusinessIdentityEngine(str(tmp_path / "identity.sqlite3"))
    item = e.create_identity(
        "tenant-1","workspace-1","Example Pty Ltd","ZA",
        {"address_line1":"1 Main Road","city":"Brakpan","province":"Gauteng","postal_code":"1540"},
        trading_name="Example", registration_number="2026/123456/07", changed_by="tester"
    )
    assert item["identity_id"].startswith("ORG-")
    assert e.get_identity("tenant-1","workspace-1",item["identity_id"])["legal_name"] == "Example Pty Ltd"
    assert e.list_identities("tenant-2","workspace-1") == []

def test_phone_validation(tmp_path):
    e = BusinessIdentityEngine(str(tmp_path / "identity.sqlite3"))
    assert e.validate_phone("ZA","+27821234567")["valid"] is True
    assert e.validate_phone("ZA","0821234567")["valid"] is False
