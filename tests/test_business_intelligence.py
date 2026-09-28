from src.core.business_intelligence import BusinessIntelligence


def test_bi_health():
    b = BusinessIntelligence()
    assert b.health()["status"] == "ok"
    assert b.health()["credentials_exposed"] is False


def test_metric_dashboard_governance():
    b = BusinessIntelligence()
    metric = b.register_metric("Revenue", "Total recognised revenue", "Finance",
                                "ledger", "v1")
    blocked_metric = b.approve_metric(metric["metric_id"])
    active = b.approve_metric(metric["metric_id"], approved=True)
    dashboard = b.create_dashboard("Executive KPI", [metric["metric_id"]])
    blocked_dashboard = b.publish_dashboard(dashboard["dashboard_id"])
    published = b.publish_dashboard(dashboard["dashboard_id"], approved=True)
    assert blocked_metric["allowed"] is False
    assert active["status"] == "active"
    assert blocked_dashboard["allowed"] is False
    assert published["status"] == "published"


def test_anomaly_trend_and_report():
    b = BusinessIntelligence()
    metric = b.register_metric("Sales", "Sales amount", "Sales", "crm", "v1")
    anomaly = b.detect_anomaly(metric["metric_id"], [10, 11, 10, 12, 11, 40])
    trend = b.detect_trend([10, 12, 15])
    report = b.create_report("Monthly BI", "crm", 0.95)
    assert anomaly["anomaly"] is True
    assert trend["direction"] == "up"
    assert report["status"] == "draft"
