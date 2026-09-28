from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import yaml

@dataclass(frozen=True)
class ITDocument:
    document_id: str
    domain: str
    title: str
    tags: tuple[str, ...]
    content: str
    source_type: str

@dataclass(frozen=True)
class ITHit:
    document: ITDocument
    score: int

class ITSupportRAG:
    """Small deterministic local knowledge layer; unmatched questions are not guessed."""
    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "it_support_knowledge.yaml"
        data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))
        source_type = data.get("retrieval", {}).get("source_type", "local_approved")
        self.max_results = int(data.get("retrieval", {}).get("max_results", 3))
        self.minimum_score = int(data.get("retrieval", {}).get("minimum_score", 1))
        self.documents = [ITDocument(d["id"], d["domain"], d["title"], tuple(d.get("tags", [])), d["content"], source_type) for d in data.get("documents", [])]

    def search(self, query: str, domain: str | None = None) -> list[ITHit]:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        hits: list[ITHit] = []
        for doc in self.documents:
            if domain and doc.domain != domain:
                continue
            haystack = set(re.findall(r"[a-z0-9]+", (" ".join(doc.tags) + " " + doc.title + " " + doc.content).lower()))
            score = len(tokens & haystack)
            if score >= self.minimum_score:
                hits.append(ITHit(doc, score))
        hits.sort(key=lambda h: (-h.score, h.document.document_id))
        return hits[: self.max_results]

    @staticmethod
    def provenance(hits: list[ITHit]) -> list[dict[str, Any]]:
        return [{"document_id": h.document.document_id, "title": h.document.title, "domain": h.document.domain, "source_type": h.document.source_type, "score": h.score} for h in hits]
