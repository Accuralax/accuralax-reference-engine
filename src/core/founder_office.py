from __future__ import annotations
from .document_models import DocumentRequest
from .document_classifier import classify_request
from .document_specialists import select_specialist

class FounderOffice:
    def route(self, request: str) -> dict:
        classified = classify_request(request)
        specialist = select_specialist(classified.document_type)
        return {
            "role": "founder_office_agent",
            "document_type": classified.document_type,
            "specialist": specialist,
            "requires_founder_approval": True,
            "credentials_exposed": False,
        }
