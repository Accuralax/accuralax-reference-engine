from src.core.sales_marketing import SalesMarketing


def test_sales_marketing_health():
    sm = SalesMarketing()
    assert sm.health()["status"] == "ok"
    assert sm.health()["credentials_exposed"] is False


def test_campaign_activation_requires_policy_approval():
    sm = SalesMarketing()
    campaign = sm.create_campaign("Launch", "email")
    blocked = sm.activate_campaign(campaign["campaign_id"])
    assert blocked["allowed"] is False
    allowed = sm.activate_campaign(campaign["campaign_id"], approved=True)
    assert allowed["allowed"] is True
    assert allowed["status"] == "active"


def test_outreach_requires_consent_and_approval():
    sm = SalesMarketing()
    campaign = sm.create_campaign("Launch", "whatsapp")
    outreach = sm.plan_outreach("CON-1", campaign["campaign_id"], "whatsapp")
    no_consent = sm.send_outreach(outreach["outreach_id"], consented=False, approved=True)
    assert no_consent["allowed"] is False
    blocked = sm.send_outreach(outreach["outreach_id"], consented=True)
    assert blocked["allowed"] is False
    sent = sm.send_outreach(outreach["outreach_id"], consented=True, approved=True)
    assert sent["allowed"] is True


def test_pipeline_attribution_and_follow_up():
    sm = SalesMarketing()
    campaign = sm.create_campaign("Launch", "social")
    sm.plan_outreach("CON-2", campaign["campaign_id"], "social")
    sm.record_attribution("LEAD-1", "website", campaign["campaign_id"], "social")
    sm.schedule_follow_up("CON-2", "2026-10-01T09:00:00Z", "proposal follow-up")
    metrics = sm.pipeline_intelligence()
    assert metrics["outreach_planned"] == 1
    assert len(sm.attribution) == 1
    assert len(sm.follow_ups) == 1
