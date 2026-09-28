from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import yaml


@dataclass(frozen=True)
class BusinessKnowledgeHit:
    document_id: str
    function: str
    title: str
    score: int
    source_type: str


class BusinessFunctionRAG:
    """Deterministic approved-knowledge retrieval for the 15 business functions."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or Path(__file__).resolve().parent.parent / "knowledge" / "business_functions_knowledge.yaml"
        self.data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) > 2}

    def search(self, query: str, *, function: str | None = None) -> list[BusinessKnowledgeHit]:
        query_tokens = self._tokens(query)
        hits: list[BusinessKnowledgeHit] = []
        for doc in self.data.get("documents", []):
            if function and doc.get("function") != function:
                continue
            corpus = " ".join([
                str(doc.get("title", "")),
                " ".join(doc.get("tags", [])),
                str(doc.get("content", "")),
            ])
            score = len(query_tokens & self._tokens(corpus))
            if score >= int(self.data.get("retrieval", {}).get("minimum_score", 1)):
                hits.append(BusinessKnowledgeHit(
                    document_id=str(doc["id"]),
                    function=str(doc["function"]),
                    title=str(doc["title"]),
                    score=score,
                    source_type=str(self.data.get("retrieval", {}).get("source_type", "local_approved")),
                ))
        hits.sort(key=lambda item: (-item.score, item.document_id))
        return hits[: int(self.data.get("retrieval", {}).get("max_results", 3))]

    @staticmethod
    def provenance(hits: list[BusinessKnowledgeHit]) -> list[dict[str, Any]]:
        return [
            {
                "document_id": hit.document_id,
                "function": hit.function,
                "title": hit.title,
                "score": hit.score,
                "source_type": hit.source_type,
            }
            for hit in hits
        ]

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": "local_approved",
            "document_count": len(self.data.get("documents", [])),
            "max_results": self.data.get("retrieval", {}).get("max_results", 3),
            "provenance": True,
            "credentials_exposed_to_agents": False,
        }
