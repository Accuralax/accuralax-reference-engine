from __future__ import annotations
from .document_classifier import classify_request
from .document_template_engine import DocumentTemplateEngine
from .document_theme_engine import DocumentThemeEngine
from .document_specialists import select_specialist
from .document_models import DocumentArtifact
from .document_quality import DocumentQualityGate

class DocumentSupervisor:
    def __init__(self):
        self.templates = DocumentTemplateEngine()
        self.themes = DocumentThemeEngine()
        self.qa = DocumentQualityGate()

    def plan(self, request: str, theme: str = "corporate", reference_id: str = "CFS-DOC-PLANNED") -> dict:
        classified = classify_request(request)
        template = self.templates.select(classified.document_type)
        specialist = select_specialist(classified.document_type)
        selected_theme = self.themes.get(theme)
        if not template or not specialist:
            return {"status": "needs_clarification", "document_type": classified.document_type}
        artifact = DocumentArtifact(reference_id, classified.document_type, template.template_id, selected_theme.theme_id, specialist)
        qa = self.qa.validate(artifact)
        return {
            "status": "ready_for_draft" if qa["passed"] else "needs_revision",
            "artifact": artifact.__dict__,
            "template_sections": template.sections,
            "theme": selected_theme.__dict__,
            "specialist": specialist,
            "qa": qa,
            "founder_approval_required": True,
            "credentials_exposed": False,
        }
