from __future__ import annotations
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
from .document_models import DocumentTemplate

class DocumentTemplateEngine:
    def __init__(self, path: str = "src/config/document_templates.yaml"):
        self.path = Path(path)
        if not self.path.is_absolute():
            self.path = BASE_DIR / "config" / self.path.name
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.templates = {
            key: DocumentTemplate(template_id=key, **value)
            for key, value in raw["templates"].items()
        }

    def get(self, template_id: str) -> DocumentTemplate | None:
        return self.templates.get(template_id)

    def select(self, document_type: str | None) -> DocumentTemplate | None:
        if not document_type:
            return None
        return self.templates.get(document_type)

    def validate(self, template: DocumentTemplate) -> bool:
        return bool(template.template_id and template.sections and template.approval)
