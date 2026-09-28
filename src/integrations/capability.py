from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CapabilityBinding:
    canonical: str
    system: str
    action: str
    side_effect: bool = False

HUBSPOT = {
    "crm.contact.search": CapabilityBinding("crm.contact.search","hubspot","search_contact"),
    "crm.contact.create": CapabilityBinding("crm.contact.create","hubspot","create_contact",True),
    "crm.contact.update": CapabilityBinding("crm.contact.update","hubspot","update_contact",True),
    "crm.company.search": CapabilityBinding("crm.company.search","hubspot","search_company"),
    "crm.company.create": CapabilityBinding("crm.company.create","hubspot","create_company",True),
    "crm.deal.search": CapabilityBinding("crm.deal.search","hubspot","search_deal"),
    "crm.deal.create": CapabilityBinding("crm.deal.create","hubspot","create_deal",True),
    "crm.deal.update": CapabilityBinding("crm.deal.update","hubspot","update_deal",True),
    "crm.task.create": CapabilityBinding("crm.task.create","hubspot","create_task",True),
}
MAKE = {
    "automation.webhook.trigger": CapabilityBinding("automation.webhook.trigger","make","trigger_webhook",True),
    "automation.scenario.status": CapabilityBinding("automation.scenario.status","make","read_scenario_status"),
}
CAPABILITIES = {**HUBSPOT, **MAKE}

def resolve(capability: str) -> CapabilityBinding | None:
    return CAPABILITIES.get(capability)

def describe() -> list[dict]:
    return [b.__dict__.copy() for b in CAPABILITIES.values()]
