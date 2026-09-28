from __future__ import annotations
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
from .document_models import DocumentTheme

class DocumentThemeEngine:
    def __init__(self, path: str = "src/config/document_themes.yaml"):
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = BASE_DIR / "config" / config_path.name
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.themes = {
            key: DocumentTheme(theme_id=key, **value)
            for key, value in raw["themes"].items()
        }

    def get(self, theme_id: str | None) -> DocumentTheme | None:
        return self.themes.get(theme_id or "corporate")

    def generate(self, style: str, palette: str = "brand_neutral") -> DocumentTheme:
        return DocumentTheme("generated", style, "modern", palette, "balanced")

    def snapshot(self) -> dict:
        return {"themes": list(self.themes), "count": len(self.themes)}
