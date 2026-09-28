from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
import json
import re


@dataclass
class CreativeAsset:
    asset_id: str
    asset_type: str
    title: str
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1


@dataclass
class CreativeToolResult:
    operation: str
    content: str
    changed: bool
    safe: bool = True


class CreativeStudio:
    """Shared deterministic foundation for document, content, image and video workflows."""

    ASSET_TYPES = {"document", "content", "image", "video", "presentation"}
    EDIT_OPERATIONS = {
        "rewrite", "expand", "shorten", "simplify", "professionalise",
        "summarise", "translate", "add_section", "remove_section",
        "apply_theme", "consistency_check",
    }

    def create_asset(self, asset_id: str, asset_type: str, title: str, content: str = "", **metadata: Any) -> CreativeAsset:
        if asset_type not in self.ASSET_TYPES:
            raise ValueError(f"Unsupported asset type: {asset_type}")
        return CreativeAsset(asset_id, asset_type, title, content, self._safe(metadata))

    def edit(self, asset: CreativeAsset, operation: str, instruction: str = "") -> CreativeToolResult:
        if operation not in self.EDIT_OPERATIONS:
            raise ValueError(f"Unsupported creative edit operation: {operation}")
        text = asset.content
        if operation == "shorten":
            paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p]
            text = "\n\n".join(paragraphs[: max(1, (len(paragraphs) + 1) // 2)])
        elif operation == "simplify":
            text = re.sub(r"\butili[sz]e\b", "use", text, flags=re.I)
            text = re.sub(r"\bfacilitate\b", "help", text, flags=re.I)
        elif operation == "professionalise":
            text = text.strip()
            if text and text[-1] not in ".!?":
                text += "."
        elif operation == "expand":
            text = f"{text}\n\n[Expansion requested: {instruction or 'add useful detail while preserving source facts.'}]".strip()
        elif operation == "rewrite":
            text = f"[Rewrite requested: {instruction or 'rewrite while preserving verified meaning.'}]\n\n{text}".strip()
        elif operation == "summarise":
            sentences = re.split(r"(?<=[.!?])\s+", text.strip())
            text = " ".join(sentences[:3])
        elif operation == "add_section":
            heading = instruction or "New Section"
            text = f"{text}\n\n## {heading}\n\n[Content to be completed by the assigned agent.]".strip()
        elif operation == "remove_section":
            pattern = rf"(?ms)^##\s+{re.escape(instruction)}\s*$.*?(?=^##\s+|\Z)"
            text = re.sub(pattern, "", text).strip()
        return CreativeToolResult(operation, text, text != asset.content)

    def render_web(self, asset: CreativeAsset, theme: dict[str, Any] | None = None) -> str:
        theme = theme or {}
        palette = theme.get("palette", {})
        background = escape(str(palette.get("background", "#ffffff")))
        foreground = escape(str(palette.get("foreground", "#172033")))
        accent = escape(str(palette.get("accent", "#2563eb")))
        body = escape(asset.content).replace("\n", "<br>\n")
        title = escape(asset.title)
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                f"<title>{title}</title><style>body{{margin:0;padding:48px;font-family:Inter,Arial,sans-serif;"
                f"background:{background};color:{foreground};line-height:1.7}}main{{max-width:920px;margin:auto}}"
                f"h1{{color:{accent}}}.meta{{opacity:.7;font-size:.9rem}}</style></head><body><main>"
                f"<h1>{title}</h1><div class='meta'>CyberFusion Creative Studio • v{asset.version}</div>"
                f"<hr><section>{body}</section></main></body></html>")

    def export_manifest(self, asset: CreativeAsset, formats: list[str]) -> dict[str, Any]:
        return {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type,
            "title": asset.title,
            "version": asset.version,
            "formats": formats,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "credentials_exposed": False,
        }

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): CreativeStudio._safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [CreativeStudio._safe(v) for v in value]
        return value
