from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

@dataclass
class DocumentVersion:
    version: int
    content_hash: str
    created_at: str
    operation: str
    summary: str

class DocumentVersionStore:
    def __init__(self):
        self._versions: dict[str, list[DocumentVersion]] = {}

    def add(self, document_id: str, content: str, operation: str, summary: str = "") -> DocumentVersion:
        versions = self._versions.setdefault(document_id, [])
        version = len(versions) + 1
        item = DocumentVersion(
            version=version,
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
            created_at=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            summary=summary,
        )
        versions.append(item)
        return item

    def history(self, document_id: str) -> list[DocumentVersion]:
        return list(self._versions.get(document_id, []))

    def compare_hashes(self, left: str, right: str) -> dict:
        return {"identical": left == right, "left": left, "right": right}

    def snapshot(self) -> dict:
        return {
            "documents": len(self._versions),
            "versions": sum(len(v) for v in self._versions.values()),
        }
