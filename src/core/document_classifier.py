from __future__ import annotations
from .document_models import DocumentRequest

KEYWORDS = {
    "funding_proposal": ("funding", "grant", "funder", "donor"),
    "tender_response": ("tender", "rfp", "procurement", "bid"),
    "business_plan": ("business plan", "business model", "strategy plan"),
    "proposal": ("proposal", "quotation proposal", "service proposal"),
    "executive_brief": ("executive brief", "decision memo", "board brief"),
    "policy": ("policy", "governance policy"),
    "sop": ("sop", "standard operating procedure", "procedure"),
    "report": ("report", "assessment report", "analysis report"),
    "presentation": ("presentation", "slides", "pitch deck"),
}

def classify_document(request: str) -> str | None:
    text = request.lower()
    exact_phrases = [
        ("funding_proposal", "funding proposal"),
        ("tender_response", "tender response"),
        ("business_plan", "business plan"),
        ("executive_brief", "executive brief"),
    ]
    for name, phrase in exact_phrases:
        if phrase in text:
            return name
    matches = [name for name, words in KEYWORDS.items() if any(w in text for w in words)]
    return matches[0] if len(matches) == 1 else None

def classify_request(request: str) -> DocumentRequest:
    return DocumentRequest(request=request, document_type=classify_document(request))
