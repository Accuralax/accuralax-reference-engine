from src.core.enterprise_data_fabric import EnterpriseDataFabric


def test_ingest_is_provenance_bound_and_secret_safe():
    fabric = EnterpriseDataFabric()
    record = fabric.ingest("crm", "customer", {"name": "Acme", "api_key": "never-store"})
    assert record.record_id.startswith("DAT-")
    assert "api_key" not in record.payload
    assert record.content_hash


def test_quality_and_metric_definition():
    fabric = EnterpriseDataFabric()
    quality = fabric.validate_quality([1, 2, 3, 4])
    assert quality["status"] == "pass"
    metric = fabric.define_metric("revenue", "finance", "ledger", "v1")
    assert metric["allowed"]


def test_intelligence_detects_trend_and_anomaly():
    fabric = EnterpriseDataFabric()
    result = fabric.analyze([10, 11, 10, 12, 11, 40])
    assert result["trend"] == "up"
    assert 40 in result["anomalies"]
    assert result["confidence"] == "medium"
