from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SecurityDocument:
    document_id: str
    domain: str
    title: str
    tags: tuple[str, ...]
    content: str
    source_type: str = "local_approved"


@dataclass(frozen=True)
class SecurityHit:
    document_id: str
    title: str
    domain: str
    score: int
    content: str
    source_type: str


class SecurityKnowledgeRAG:
    """Deterministic local retrieval with provenance; embeddings can be added later."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "security_knowledge.yaml"
        data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))
        self.documents = tuple(
            SecurityDocument(
                document_id=str(item["id"]),
                domain=str(item["domain"]),
                title=str(item["title"]),
                tags=tuple(str(tag).lower() for tag in item.get("tags", [])),
                content=str(item["content"]),
            )
            for item in data.get("documents", [])
        )
        retrieval = data.get("retrieval", {})
        self.max_results = int(retrieval.get("max_results", 3))
        self.minimum_score = int(retrieval.get("minimum_score", 1))

    def search(self, query: str, *, domain: str | None = None) -> list[SecurityHit]:
        terms = {term.strip(".,:;!?()[]{}").lower() for term in query.split() if len(term.strip()) > 2}
        hits: list[SecurityHit] = []
        for doc in self.documents:
            if domain and doc.domain != domain:
                continue
            score = sum(1 for term in terms if term in doc.tags or term in doc.title.lower() or term in doc.content.lower())
            if score >= self.minimum_score:
                hits.append(SecurityHit(doc.document_id, doc.title, doc.domain, score, doc.content, doc.source_type))
        return sorted(hits, key=lambda item: (-item.score, item.document_id))[: self.max_results]

    def provenance(self, hits: list[SecurityHit]) -> list[dict[str, str | int]]:
        return [
            {"document_id": hit.document_id, "title": hit.title, "source_type": hit.source_type, "score": hit.score}
            for hit in hits
        ]
