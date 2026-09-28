from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import uuid
import yaml


class CRMCustomer:
    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "crm_customer.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.contacts: dict[str, dict[str, Any]] = {}
        self.leads: dict[str, dict[str, Any]] = {}
        self.opportunities: dict[str, dict[str, Any]] = {}
        self.interactions: list[dict[str, Any]] = []
        self.consents: dict[str, dict[str, Any]] = {}

    def create_contact(self, name: str, email: str, client_type: str) -> dict[str, Any]:
        if any(c["email"].lower() == email.lower() for c in self.contacts.values()):
            raise ValueError("duplicate contact")
        contact = {"contact_id": f"CON-{uuid.uuid4().hex[:10].upper()}", "name": name,
                   "email": email, "client_type": client_type, "created_at": datetime.now(timezone.utc).isoformat()}
        self.contacts[contact["contact_id"]] = contact
        return contact

    def record_consent(self, contact_id: str, purpose: str, granted: bool) -> dict[str, Any]:
        if contact_id not in self.contacts:
            raise ValueError("unknown contact")
        consent = {"consent_id": f"CNS-{uuid.uuid4().hex[:10].upper()}", "contact_id": contact_id,
                   "purpose": purpose, "granted": granted, "recorded_at": datetime.now(timezone.utc).isoformat()}
        self.consents[f"{contact_id}:{purpose}"] = consent
        return consent

    def create_lead(self, contact_id: str, scores: dict[str, int]) -> dict[str, Any]:
        required = self.config["lead_scoring"]["dimensions"]
        if any(k not in scores for k in required):
            raise ValueError("incomplete lead score")
        total = sum(scores.values())
        label = "high" if total >= 80 else "medium" if total >= 50 else "low"
        lead = {"lead_id": f"LED-{uuid.uuid4().hex[:10].upper()}", "contact_id": contact_id,
                "scores": scores, "score": total, "label": label, "stage": "new"}
        self.leads[lead["lead_id"]] = lead
        return lead

    def handoff(self, contact_id: str, destination: str, consented: bool) -> dict[str, Any]:
        if not consented:
            return {"allowed": False, "reason": "explicit_consent_required"}
        return {"allowed": True, "handoff_id": f"HND-{uuid.uuid4().hex[:10].upper()}",
                "contact_id": contact_id, "destination": destination, "consent": True}

    def record_interaction(self, contact_id: str, channel: str, summary: str) -> dict[str, Any]:
        event = {"interaction_id": f"INT-{uuid.uuid4().hex[:10].upper()}", "contact_id": contact_id,
                 "channel": channel, "summary": summary, "occurred_at": datetime.now(timezone.utc).isoformat()}
        self.interactions.append(event)
        return event

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "contact_count": len(self.contacts), "lead_count": len(self.leads),
                "interaction_count": len(self.interactions), "consent_count": len(self.consents),
                "credentials_exposed": False}
