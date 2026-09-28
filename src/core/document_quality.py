from __future__ import annotations
from .document_models import DocumentArtifact

class DocumentQualityGate:
    def validate(self, artifact: DocumentArtifact) -> dict:
        checks = {
            "reference_id": bool(artifact.reference_id),
            "document_type": bool(artifact.document_type),
            "template": bool(artifact.template_id),
            "theme": bool(artifact.theme_id),
            "specialist": bool(artifact.specialist),
        }
        passed = all(checks.values())
        return {"passed": passed, "checks": checks, "status": "approved_for_review" if passed else "needs_revision"}
