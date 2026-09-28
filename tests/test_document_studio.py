from src.core.document_classifier import classify_document
from src.core.document_specialists import select_specialist
from src.core.document_supervisor import DocumentSupervisor

def test_classification():
    assert classify_document("Prepare a funding proposal") == "funding_proposal"

def test_specialist():
    assert select_specialist("tender_response") == "tender_agent"

def test_supervisor_plan():
    result = DocumentSupervisor().plan("Create a business plan", theme="executive")
    assert result["status"] == "ready_for_draft"
    assert result["founder_approval_required"] is True
    assert result["credentials_exposed"] is False
    assert "executive_summary" in result["template_sections"]

def test_ambiguous_request():
    result = DocumentSupervisor().plan("Create something for the company")
    assert result["status"] == "needs_clarification"
