from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class DocumentRequest:
    request: str
    document_type: str | None = None
    audience: str | None = None
    theme: str | None = None
    organisation: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentTemplate:
    template_id: str
    document_type: str
    audience: str
    sections: list[str]
    approval: str

@dataclass
class DocumentTheme:
    theme_id: str
    style: str
    typography: str
    palette: str
    spacing: str

@dataclass
class DocumentArtifact:
    reference_id: str
    document_type: str
    template_id: str
    theme_id: str
    specialist: str
    status: str = "draft"
    content: dict[str, Any] = field(default_factory=dict)
    qa: dict[str, Any] = field(default_factory=dict)
