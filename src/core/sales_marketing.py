from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from .crm_customer import CRMCustomer
from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


@dataclass
class Campaign:
    campaign_id: str
    name: str
    channel: str
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)


class SalesMarketing:
    """Governed sales, marketing, outreach and pipeline intelligence."""

    def __init__(self) -> None:
        self.campaigns: dict[str, Campaign] = {}
        self.outreach: list[dict[str, Any]] = []
        self.proposals: dict[str, dict[str, Any]] = {}
        self.follow_ups: list[dict[str, Any]] = []
        self.attribution: list[dict[str, Any]] = []
        self.crm = CRMCustomer()
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    def create_campaign(self, name: str, channel: str) -> dict[str, Any]:
        campaign_id = f"CMP-{uuid.uuid4().hex[:10].upper()}"
        campaign = Campaign(campaign_id, name, channel)
        self.campaigns[campaign_id] = campaign
        self.lineage.record("campaign.created", "system", "campaign", campaign_id, "sales_marketing")
        return self._safe({"campaign_id": campaign_id, "status": campaign.status})

    def activate_campaign(self, campaign_id: str, approved: bool = False) -> dict[str, Any]:
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {"allowed": False, "reason": "campaign_not_found"}
        decision = self.policy.evaluate("external_side_effects", approved=approved,
                                       context={"policy_check_passed": approved})
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        campaign.status = "active"
        self.lineage.record("campaign.activated", "operator", "campaign", campaign_id, "sales_marketing")
        return {"allowed": True, "campaign_id": campaign_id, "status": campaign.status}

    def plan_outreach(self, contact_id: str, campaign_id: str, channel: str) -> dict[str, Any]:
        if campaign_id not in self.campaigns:
            return {"allowed": False, "reason": "campaign_not_found"}
        item = {
            "outreach_id": f"OUT-{uuid.uuid4().hex[:10].upper()}",
            "contact_id": contact_id,
            "campaign_id": campaign_id,
            "channel": channel,
            "status": "planned",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.outreach.append(item)
        return self._safe(item)

    def send_outreach(self, outreach_id: str, consented: bool, approved: bool = False) -> dict[str, Any]:
        item = next((x for x in self.outreach if x["outreach_id"] == outreach_id), None)
        if not item:
            return {"allowed": False, "reason": "outreach_not_found"}
        if not consented:
            item["status"] = "opted_out"
            return {"allowed": False, "reason": "marketing_consent_required"}
        decision = self.policy.evaluate("external_side_effects", approved=approved,
                                       context={"policy_check_passed": approved})
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item["status"] = "sent"
        self.lineage.record("outreach.sent", "operator", "outreach", outreach_id, "sales_marketing")
        return {"allowed": True, "outreach_id": outreach_id, "status": "sent"}

    def create_proposal(self, opportunity_id: str, *, approved: bool = False) -> dict[str, Any]:
        proposal_id = f"PRP-{uuid.uuid4().hex[:10].upper()}"
        status = "approved" if approved else "draft"
        self.proposals[proposal_id] = {
            "proposal_id": proposal_id,
            "opportunity_id": opportunity_id,
            "status": status,
        }
        self.lineage.record("proposal.created", "system", "proposal", proposal_id, "sales_marketing")
        return self._safe(self.proposals[proposal_id])

    def schedule_follow_up(self, contact_id: str, when: str, reason: str) -> dict[str, Any]:
        item = {
            "follow_up_id": f"FUP-{uuid.uuid4().hex[:10].upper()}",
            "contact_id": contact_id,
            "when": when,
            "reason": reason,
            "status": "scheduled",
        }
        self.follow_ups.append(item)
        return self._safe(item)

    def record_attribution(self, lead_id: str, source: str, campaign: str, channel: str) -> dict[str, Any]:
        item = {
            "lead_id": lead_id,
            "source": source,
            "campaign": campaign,
            "channel": channel,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.attribution.append(item)
        return self._safe(item)

    def pipeline_intelligence(self) -> dict[str, Any]:
        total = len(self.outreach)
        sent = sum(x["status"] == "sent" for x in self.outreach)
        return {
            "outreach_planned": total,
            "outreach_sent": sent,
            "response_rate": 0.0,
            "confidence": "low" if total == 0 else "observed",
            "credentials_exposed": False,
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "campaigns": len(self.campaigns),
            "outreach": len(self.outreach),
            "proposals": len(self.proposals),
            "follow_ups": len(self.follow_ups),
            "attribution": len(self.attribution),
            "credentials_exposed": False,
            "lineage": self.lineage.health(),
        }

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): SalesMarketing._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [SalesMarketing._safe(v) for v in value]
        return value
