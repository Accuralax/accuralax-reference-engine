SPECIALISTS = {
    "executive_brief": "founder_office_agent",
    "proposal": "proposal_agent",
    "business_plan": "business_plan_agent",
    "funding_proposal": "funding_agent",
    "tender_response": "tender_agent",
    "report": "report_agent",
    "policy": "policy_sop_agent",
    "sop": "policy_sop_agent",
    "presentation": "presentation_agent",
}

def select_specialist(document_type: str | None) -> str | None:
    return SPECIALISTS.get(document_type)

def snapshot() -> dict:
    return {"specialists": dict(SPECIALISTS), "count": len(SPECIALISTS)}
